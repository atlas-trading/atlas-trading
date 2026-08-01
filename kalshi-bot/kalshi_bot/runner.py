import argparse
import asyncio
import logging
import time

import aiohttp

from kalshi_bot.client import KalshiPublicClient, KalshiTradingClient, RsaRequestSigner
from kalshi_bot.config import BotConfig, load_config
from kalshi_bot.executor import BasketExecutor
from kalshi_bot.scanner import detect
from kalshi_bot.store import Store

logger = logging.getLogger(__name__)


async def run(
    *,
    config: BotConfig,
    execute: bool,
    once: bool,
    max_pages: int | None,
) -> None:
    store = Store(config.db_path)
    executed_events: set[str] = set()
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            public = KalshiPublicClient(base_url=config.public_base_url, session=session)
            executor = _build_executor(config, session, public, store) if execute else None
            while True:
                started = time.monotonic()
                try:
                    await _scan_once(
                        config, public, store, executor, executed_events, max_pages=max_pages
                    )
                except aiohttp.ClientError as exc:
                    logger.error("scan failed: %s", exc)
                if once:
                    return
                elapsed = time.monotonic() - started
                await asyncio.sleep(max(0.0, config.poll_interval_seconds - elapsed))
    finally:
        store.close()


async def _scan_once(
    config: BotConfig,
    public: KalshiPublicClient,
    store: Store,
    executor: BasketExecutor | None,
    executed_events: set[str],
    *,
    max_pages: int | None = None,
) -> None:
    events = await public.list_open_events(max_pages=max_pages)
    found = 0
    for event in events:
        for opportunity in detect(event, config):
            opportunity_id = store.record_opportunity(opportunity)
            found += 1
            logger.info(
                "opportunity %s %s legs=%d count=%s net=%s executable=%s",
                opportunity.kind.value,
                opportunity.event_ticker,
                len(opportunity.legs),
                opportunity.count,
                opportunity.net_edge_total,
                opportunity.executable,
            )
            if (
                executor is not None
                and opportunity.executable
                and opportunity.event_ticker not in executed_events
            ):
                executed_events.add(opportunity.event_ticker)
                await executor.execute(opportunity, opportunity_id)
    logger.info("scanned %d events, %d opportunities", len(events), found)


def _build_executor(
    config: BotConfig,
    session: aiohttp.ClientSession,
    public: KalshiPublicClient,
    store: Store,
) -> BasketExecutor:
    if config.env != "demo":
        raise SystemExit("--execute는 demo 환경에서만 허용됩니다 (KALSHI_ENV=demo)")
    if not config.api_key_id or not config.private_key_path:
        raise SystemExit("KALSHI_API_KEY_ID / KALSHI_PRIVATE_KEY_PATH 환경변수가 필요합니다")
    signer = RsaRequestSigner.from_file(
        api_key_id=config.api_key_id, private_key_path=config.private_key_path
    )
    trading = KalshiTradingClient(
        base_url=config.trading_base_url, session=session, signer=signer
    )
    return BasketExecutor(
        trading=trading,
        public=public,
        store=store,
        max_total_exposure=config.max_total_exposure,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Kalshi structural arbitrage bot")
    parser.add_argument("--env", choices=["prod", "demo"], default=None)
    parser.add_argument("--execute", action="store_true", help="데모 계정에 실제 주문")
    parser.add_argument("--once", action="store_true", help="1회 스캔 후 종료")
    parser.add_argument("--max-pages", type=int, default=None, help="이벤트 페이지 수 제한")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    config = load_config(env=args.env)
    asyncio.run(
        run(config=config, execute=args.execute, once=args.once, max_pages=args.max_pages)
    )


if __name__ == "__main__":
    main()
