import asyncio
import logging
from decimal import Decimal, InvalidOperation

import aiohttp

from kalshi_bot.backtest.candle import Candle

logger = logging.getLogger(__name__)

MAX_CANDLES_PER_REQUEST = 4900
RETRY_DELAYS = (1.0, 3.0, 10.0)


class HistoryClient:
    """정산 마켓 탐색과 캔들스틱 조회 (공개 API, 인증 불필요)."""

    def __init__(
        self,
        *,
        base_url: str,
        session: aiohttp.ClientSession,
        concurrency: int = 5,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._semaphore = asyncio.Semaphore(concurrency)

    async def settled_event_tickers(
        self, *, start_ts: int, end_ts: int, max_events: int
    ) -> list[str]:
        tickers: dict[str, None] = {}
        cursor: str | None = None
        while len(tickers) < max_events:
            params = {
                "status": "settled",
                "min_close_ts": str(start_ts),
                "max_close_ts": str(end_ts),
                "limit": "200",
            }
            if cursor:
                params["cursor"] = cursor
            payload = await self._get("/markets", params)
            for market in payload.get("markets", []):
                event_ticker = market.get("event_ticker")
                # MVE(팔레이 조합상품)는 단일마켓 이벤트라 바스켓 차익 대상이 아님
                if event_ticker and not market.get("mve_collection_ticker"):
                    tickers.setdefault(event_ticker, None)
            cursor = payload.get("cursor")
            if not cursor:
                break
        return list(tickers)[:max_events]

    async def get_event(self, event_ticker: str) -> dict:
        payload = await self._get(
            f"/events/{event_ticker}", {"with_nested_markets": "true"}
        )
        return payload.get("event", {})

    async def get_candles(
        self,
        *,
        series_ticker: str,
        market_ticker: str,
        start_ts: int,
        end_ts: int,
        interval_minutes: int,
    ) -> list[Candle]:
        candles: list[Candle] = []
        chunk_span = MAX_CANDLES_PER_REQUEST * interval_minutes * 60
        chunk_start = start_ts
        while chunk_start < end_ts:
            chunk_end = min(chunk_start + chunk_span, end_ts)
            payload = await self._get(
                f"/series/{series_ticker}/markets/{market_ticker}/candlesticks",
                {
                    "start_ts": str(chunk_start),
                    "end_ts": str(chunk_end),
                    "period_interval": str(interval_minutes),
                },
            )
            for raw in payload.get("candlesticks", []):
                candle = parse_candle(raw)
                if candle is not None:
                    candles.append(candle)
            chunk_start = chunk_end
        return candles

    async def _get(self, path: str, params: dict) -> dict:
        async with self._semaphore:
            for delay in (*RETRY_DELAYS, None):
                async with self._session.get(
                    f"{self._base_url}{path}", params=params
                ) as response:
                    if response.status == 429 and delay is not None:
                        logger.warning("rate limited on %s, retrying in %.0fs", path, delay)
                        await asyncio.sleep(delay)
                        continue
                    response.raise_for_status()
                    return await response.json()
            raise RuntimeError("unreachable")


def parse_candle(raw: dict) -> Candle | None:
    end_ts = raw.get("end_period_ts")
    yes_bid = raw.get("yes_bid") or {}
    yes_ask = raw.get("yes_ask") or {}
    if end_ts is None or not yes_bid or not yes_ask:
        return None
    try:
        return Candle(
            end_ts=int(end_ts),
            yes_bid_close=Decimal(yes_bid["close_dollars"]),
            yes_bid_low=Decimal(yes_bid["low_dollars"]),
            yes_ask_close=Decimal(yes_ask["close_dollars"]),
            yes_ask_high=Decimal(yes_ask["high_dollars"]),
        )
    except (KeyError, InvalidOperation):
        return None
