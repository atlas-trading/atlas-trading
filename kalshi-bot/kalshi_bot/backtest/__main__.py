import argparse
import asyncio
import json
import logging
import time

import aiohttp

from kalshi_bot.backtest.history import HistoryClient
from kalshi_bot.backtest.replay import EventReplayResult, replay_event
from kalshi_bot.backtest.report import build_summary, format_summary
from kalshi_bot.config import load_config

logger = logging.getLogger("kalshi_bot.backtest")

MAX_LEGS = 40


async def run_backtest(
    *,
    days: int,
    interval_minutes: int,
    mode: str,
    max_events: int,
    out_path: str | None,
) -> None:
    config = load_config(env="prod")
    end_ts = int(time.time())
    start_ts = end_ts - days * 86400
    results: list[EventReplayResult] = []
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60)
    ) as session:
        client = HistoryClient(base_url=config.public_base_url, session=session)
        event_tickers = await client.settled_event_tickers(
            start_ts=start_ts, end_ts=end_ts, max_events=max_events
        )
        logger.info("found %d settled events in window", len(event_tickers))
        skipped = 0
        for index, event_ticker in enumerate(event_tickers, start=1):
            event = await client.get_event(event_ticker)
            markets = event.get("markets") or []
            if (
                not event.get("mutually_exclusive")
                or not 2 <= len(markets) <= MAX_LEGS
                or not event.get("series_ticker")
            ):
                skipped += 1
                continue
            candle_lists = await asyncio.gather(
                *(
                    client.get_candles(
                        series_ticker=event["series_ticker"],
                        market_ticker=market["ticker"],
                        start_ts=start_ts,
                        end_ts=end_ts,
                        interval_minutes=interval_minutes,
                    )
                    for market in markets
                )
            )
            result = replay_event(
                event_ticker=event_ticker,
                title=event.get("title", ""),
                mutually_exclusive=True,
                candles_by_market={
                    market["ticker"]: candles
                    for market, candles in zip(markets, candle_lists, strict=True)
                },
                config=config,
                mode=mode,  # type: ignore[arg-type]
            )
            results.append(result)
            if result.hits:
                logger.info(
                    "%s: %d hits in %d bars", event_ticker, len(result.hits),
                    result.bars_replayed,
                )
            if index % 20 == 0:
                logger.info("progress %d/%d", index, len(event_tickers))
        logger.info("skipped %d events (not mutually exclusive / leg count)", skipped)
    if out_path:
        _dump_hits(results, out_path)
    print(format_summary(build_summary(results)))


def _dump_hits(results: list[EventReplayResult], out_path: str) -> None:
    with open(out_path, "w") as fh:
        for result in results:
            for hit in result.hits:
                opportunity = hit.opportunity
                fh.write(
                    json.dumps(
                        {
                            "ts": hit.ts,
                            "event_ticker": opportunity.event_ticker,
                            "kind": opportunity.kind.value,
                            "count": str(opportunity.count),
                            "gross_edge_total": str(opportunity.gross_edge_total),
                            "fee_total": str(opportunity.fee_total),
                            "net_edge_total": str(opportunity.net_edge_total),
                            "executable": opportunity.executable,
                            "legs": [
                                {
                                    "ticker": leg.ticker,
                                    "side": leg.side,
                                    "price": str(leg.price),
                                }
                                for leg in opportunity.legs
                            ],
                        }
                    )
                    + "\n"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Kalshi candlestick replay backtest")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--interval", type=int, choices=[1, 60, 1440], default=60)
    parser.add_argument("--mode", choices=["close", "conservative"], default="close")
    parser.add_argument("--max-events", type=int, default=200)
    parser.add_argument("--out", default=None, help="hit 상세를 저장할 JSONL 경로")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    asyncio.run(
        run_backtest(
            days=args.days,
            interval_minutes=args.interval,
            mode=args.mode,
            max_events=args.max_events,
            out_path=args.out,
        )
    )


if __name__ == "__main__":
    main()
