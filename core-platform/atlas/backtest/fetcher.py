import asyncio
import csv
import io
import logging
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import aiohttp
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from atlas.db.models import RawTick

_log = logging.getLogger(__name__)

_CCXT_TO_VISION: dict[str, str] = {
    "BTC/USDT": "BTCUSDT",
    "ETH/USDT": "ETHUSDT",
    "ETH/BTC": "ETHBTC",
    "BNB/USDT": "BNBUSDT",
    "BNB/BTC": "BNBBTC",
    "BNB/ETH": "BNBETH",
    "XRP/USDT": "XRPUSDT",
    "XRP/BTC": "XRPBTC",
    "XRP/ETH": "XRPETH",
}

_BASE_URL = (
    "https://data.binance.vision/data/spot/daily/bookTicker/{sym}/{sym}-bookTicker-{date}.zip"
)
_MAX_CONCURRENT = 20


class BinanceVisionFetcher:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def fetch(self, start: date, end: date) -> int:
        """Download [start, end) for all 9 symbols. Returns total rows inserted."""
        dates = _date_range(start, end)
        all_pairs = [(sym, d) for sym in _CCXT_TO_VISION for d in dates]

        to_fetch: list[tuple[str, date]] = []
        async with self._session_factory() as session:
            for ccxt_sym, d in all_pairs:
                if not await self._already_fetched(session, ccxt_sym, d):
                    to_fetch.append((ccxt_sym, d))

        if not to_fetch:
            _log.info("All data already fetched — skipping download")
            return 0

        _log.info("Downloading %d files (max %d concurrent)…", len(to_fetch), _MAX_CONCURRENT)
        sem = asyncio.Semaphore(_MAX_CONCURRENT)
        async with aiohttp.ClientSession() as http:
            results = await asyncio.gather(
                *[self._fetch_one(http, sem, sym, d) for sym, d in to_fetch],
                return_exceptions=True,
            )
        total = 0
        for r in results:
            if isinstance(r, int):
                total += r
            else:
                _log.warning("fetch error: %s", r)
        return total

    async def _fetch_one(
        self,
        http: aiohttp.ClientSession,
        sem: asyncio.Semaphore,
        ccxt_sym: str,
        target_date: date,
    ) -> int:
        vision_sym = _CCXT_TO_VISION[ccxt_sym]
        url = _BASE_URL.format(sym=vision_sym, date=target_date.isoformat())
        async with sem:
            try:
                async with http.get(url) as resp:
                    if resp.status == 404:
                        return 0
                    resp.raise_for_status()
                    data = await resp.read()
            except Exception as e:
                _log.warning("download failed %s %s: %s", ccxt_sym, target_date, e)
                return 0

        rows = _parse_zip(ccxt_sym, data)
        if rows:
            async with self._session_factory() as session:
                session.add_all(rows)
                await session.commit()
        return len(rows)

    async def _already_fetched(self, session, ccxt_sym: str, target_date: date) -> bool:
        day_start = datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc
        )
        day_end = day_start + timedelta(days=1)
        result = await session.execute(
            select(func.count())
            .select_from(RawTick)
            .where(
                RawTick.exchange == "binance",
                RawTick.symbol == ccxt_sym,
                RawTick.timestamp >= day_start,
                RawTick.timestamp < day_end,
            )
        )
        return result.scalar_one() > 0


def _date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days)]


def _parse_zip(ccxt_sym: str, data: bytes) -> list[RawTick]:
    """Parse a Binance Vision bookTicker zip, keeping the last row per second."""
    per_second: dict[int, tuple[str, str]] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        with zf.open(zf.namelist()[0]) as f:
            for row in csv.reader(io.TextIOWrapper(f)):
                if not row or row[0] == "update_id":
                    continue
                try:
                    event_ms = int(row[6])
                except (ValueError, IndexError):
                    continue
                per_second[event_ms // 1000] = (row[1], row[3])

    return [
        RawTick(
            exchange="binance",
            symbol=ccxt_sym,
            timestamp=datetime.fromtimestamp(sec, tz=timezone.utc),
            bid=Decimal(bid),
            ask=Decimal(ask),
            last=Decimal(0),
            volume=Decimal(0),
        )
        for sec, (bid, ask) in sorted(per_second.items())
    ]
