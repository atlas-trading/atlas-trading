# Backtest Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Binance 과거 bookTicker 데이터를 다운로드해 raw_ticks에 적재하고, 기존 삼각 차익거래 전략을 그대로 재실행해 수수료·슬리피지 반영 PnL을 산출한다.

**Architecture:** `BinanceVisionFetcher`가 Binance Vision zip을 다운로드해 1초 다운샘플 후 `raw_ticks`에 저장. `HistoricalFeed`가 DB를 스트리밍하며 `BacktestRunner`가 기존 전략/엔진을 그대로 구동. `BacktestExchange`가 가상 체결을 담당.

**Tech Stack:** Python 3.12, asyncio, aiohttp, SQLAlchemy async, aiosqlite (테스트용), pytest-asyncio

---

## 파일 구조

```
core-platform/
├── atlas/backtest/
│   ├── __init__.py          # 빈 파일
│   ├── exchange.py          # BacktestExchange: ExchangeInterface 구현, 가상 체결
│   ├── feed.py              # HistoricalFeed: raw_ticks → AsyncGenerator
│   ├── fetcher.py           # BinanceVisionFetcher: zip 다운로드 → raw_ticks 적재
│   ├── runner.py            # BacktestRunner + TradeRecord dataclass
│   └── report.py            # BacktestSummary: 터미널 출력 + CSV 저장
├── run_backtest.py          # CLI 진입점
└── tests/test_backtest/
    ├── __init__.py
    ├── test_exchange.py
    ├── test_feed.py
    ├── test_fetcher.py
    └── test_runner.py
```

---

## Task 1: BacktestExchange

**Files:**
- Create: `atlas/backtest/__init__.py`
- Create: `atlas/backtest/exchange.py`
- Create: `tests/test_backtest/__init__.py`
- Create: `tests/test_backtest/test_exchange.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_backtest/test_exchange.py
from decimal import Decimal

import pytest

from atlas.backtest.exchange import BacktestExchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus
from atlas.execution.order_type import OrderType
from atlas.execution.side import Side

_BTC_USDT = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_ETH_BTC = TradingPair(ticker=Ticker.ETH, quote=Quote.BTC)

_TICKERS = {
    "BTC/USDT": {"bid": 50000.0, "ask": 50010.0, "last": 50005.0},
    "ETH/BTC":  {"bid": 0.0666,  "ask": 0.0668,  "last": 0.0667},
}


def _order(pair: TradingPair, side: Side, qty: str = "0.01") -> Order:
    return Order(
        id="test-order",
        exchange=None,  # type: ignore[arg-type]
        trading_pair=pair,
        side=side,
        order_type=OrderType.MARKET,
        quantity=Decimal(qty),
    )


async def test_buy_fills_at_ask_plus_slippage():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("1000")}, slippage=Decimal("0.001"))
    ex.update_prices(_TICKERS)
    result = await ex.place_order(_order(_BTC_USDT, Side.BUY))
    expected_price = Decimal("50010") * Decimal("1.001")
    assert result.status == OrderStatus.FILLED
    assert result.average == expected_price


async def test_sell_fills_at_bid_minus_slippage():
    ex = BacktestExchange(
        initial_balance={"USDT": Decimal("0"), "BTC": Decimal("1")}, slippage=Decimal("0.001")
    )
    ex.update_prices(_TICKERS)
    result = await ex.place_order(_order(_BTC_USDT, Side.SELL))
    expected_price = Decimal("50000") * Decimal("0.999")
    assert result.average == expected_price


async def test_buy_deducts_quote_adds_base():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("1000")})
    ex.update_prices(_TICKERS)
    await ex.place_order(_order(_BTC_USDT, Side.BUY, "0.01"))
    assert ex.get_balance_for("USDT") < Decimal("1000")
    assert ex.get_balance_for("BTC") == Decimal("0.01")


async def test_sell_deducts_base_adds_quote():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("0"), "BTC": Decimal("0.01")})
    ex.update_prices(_TICKERS)
    await ex.place_order(_order(_BTC_USDT, Side.SELL, "0.01"))
    assert ex.get_balance_for("BTC") == Decimal("0")
    assert ex.get_balance_for("USDT") > Decimal("0")


async def test_insufficient_quote_raises():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("1")})
    ex.update_prices(_TICKERS)
    with pytest.raises(RuntimeError, match="Insufficient"):
        await ex.place_order(_order(_BTC_USDT, Side.BUY, "1"))


async def test_no_price_raises():
    ex = BacktestExchange(initial_balance={"USDT": Decimal("1000")})
    with pytest.raises(RuntimeError, match="No price"):
        await ex.place_order(_order(_BTC_USDT, Side.BUY))


async def test_health_check_always_true():
    ex = BacktestExchange(initial_balance={})
    assert await ex.health_check() is True


async def test_update_prices_ignores_unknown_symbols():
    ex = BacktestExchange(initial_balance={})
    ex.update_prices({"INVALID_SYM": {"bid": 1, "ask": 2}})  # should not raise
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd core-platform
.venv/bin/python -m pytest tests/test_backtest/test_exchange.py -v
# Expected: ImportError or ModuleNotFoundError
```

- [ ] **Step 3: `atlas/backtest/__init__.py` + `atlas/backtest/exchange.py` 구현**

```python
# atlas/backtest/__init__.py
# (empty)
```

```python
# atlas/backtest/exchange.py
from decimal import Decimal
from typing import Any

from atlas.core.parsers import parse_trading_pair, to_ccxt_symbol
from atlas.core.trading_pair import TradingPair
from atlas.exchange.exchange_interface import ExchangeInterface, TickerCallback
from atlas.exchange.order_result import OrderResult
from atlas.execution.balance import Balance
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus
from atlas.execution.side import Side


class BacktestExchange(ExchangeInterface):
    def __init__(
        self,
        initial_balance: dict[str, Decimal],
        slippage: Decimal = Decimal("0.0005"),
    ) -> None:
        self._balance: dict[str, Decimal] = dict(initial_balance)
        self._slippage = slippage
        self._prices: dict[TradingPair, tuple[Decimal, Decimal]] = {}

    def update_prices(self, tickers: dict[str, Any]) -> None:
        for symbol, data in tickers.items():
            try:
                pair = parse_trading_pair(symbol)
            except (ValueError, KeyError):
                continue
            bid = Decimal(str(data.get("bid") or 0))
            ask = Decimal(str(data.get("ask") or 0))
            if bid > 0 and ask > 0:
                self._prices[pair] = (bid, ask)

    def get_balance_for(self, currency: str) -> Decimal:
        return self._balance.get(currency, Decimal(0))

    def get_usdt_balance(self) -> Decimal:
        return self._balance.get("USDT", Decimal(0))

    async def place_order(self, order: Order) -> OrderResult:
        pair = order.trading_pair
        prices = self._prices.get(pair)
        if prices is None:
            raise RuntimeError(f"No price for {to_ccxt_symbol(pair)}")
        bid, ask = prices

        if order.side == Side.BUY:
            fill_price = ask * (1 + self._slippage)
            cost = order.quantity * fill_price
            quote = str(pair.quote)
            if self._balance.get(quote, Decimal(0)) < cost:
                raise RuntimeError(f"Insufficient {quote} balance")
            self._balance[quote] = self._balance.get(quote, Decimal(0)) - cost
            base = str(pair.ticker)
            self._balance[base] = self._balance.get(base, Decimal(0)) + order.quantity
            return OrderResult(
                id=order.id, status=OrderStatus.FILLED,
                filled=order.quantity, average=fill_price, cost=cost,
            )
        else:
            fill_price = bid * (1 - self._slippage)
            proceeds = order.quantity * fill_price
            base = str(pair.ticker)
            if self._balance.get(base, Decimal(0)) < order.quantity:
                raise RuntimeError(f"Insufficient {base} balance")
            self._balance[base] = self._balance.get(base, Decimal(0)) - order.quantity
            quote = str(pair.quote)
            self._balance[quote] = self._balance.get(quote, Decimal(0)) + proceeds
            return OrderResult(
                id=order.id, status=OrderStatus.FILLED,
                filled=order.quantity, average=fill_price, cost=proceeds,
            )

    async def get_balance(self) -> Balance:
        return Balance(
            usdt=self._balance.get("USDT", Decimal(0)),
            btc=self._balance.get("BTC", Decimal(0)),
            eth=self._balance.get("ETH", Decimal(0)),
        )

    async def health_check(self) -> bool:
        return True

    async def subscribe_ticker(self, trading_pairs: list, callback: TickerCallback) -> None:
        pass

    async def cancel_order(self, order_id: str, symbol: str) -> None:
        pass

    async def close(self) -> None:
        pass
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/python -m pytest tests/test_backtest/test_exchange.py -v
# Expected: 8 passed
```

- [ ] **Step 5: 커밋**

```bash
git add atlas/backtest/ tests/test_backtest/
git commit -m "feat(backtest): BacktestExchange with simulated fill and balance tracking"
```

---

## Task 2: HistoricalFeed

**Files:**
- Create: `atlas/backtest/feed.py`
- Create: `tests/test_backtest/test_feed.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_backtest/test_feed.py
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from atlas.backtest.feed import HistoricalFeed
from atlas.db.models import Base, RawTick


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _tick(symbol: str, ts: datetime, bid: str, ask: str) -> RawTick:
    return RawTick(
        exchange="binance",
        symbol=symbol,
        timestamp=ts,
        bid=Decimal(bid),
        ask=Decimal(ask),
        last=Decimal(0),
        volume=Decimal(0),
    )


_T1 = datetime(2025, 3, 1, 0, 0, 1, tzinfo=timezone.utc)
_T2 = datetime(2025, 3, 1, 0, 0, 2, tzinfo=timezone.utc)


async def test_stream_yields_tickers_grouped_by_timestamp(session_factory):
    async with session_factory() as s:
        s.add_all([
            _tick("BTC/USDT", _T1, "50000", "50001"),
            _tick("ETH/BTC",  _T1, "0.06",  "0.061"),
            _tick("BTC/USDT", _T2, "50100", "50101"),
        ])
        await s.commit()

    feed = HistoricalFeed(session_factory)
    results = []
    async for ts, tickers in feed.stream(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    ):
        results.append((ts, tickers))

    assert len(results) == 2  # two distinct timestamps
    ts1, t1 = results[0]
    assert ts1 == _T1
    assert "BTC/USDT" in t1 and "ETH/BTC" in t1
    assert t1["BTC/USDT"]["bid"] == 50000.0

    ts2, t2 = results[1]
    assert ts2 == _T2
    assert list(t2.keys()) == ["BTC/USDT"]


async def test_stream_respects_date_range(session_factory):
    outside = datetime(2025, 2, 28, 23, 59, 59, tzinfo=timezone.utc)
    async with session_factory() as s:
        s.add_all([
            _tick("BTC/USDT", outside, "49000", "49001"),
            _tick("BTC/USDT", _T1,    "50000", "50001"),
        ])
        await s.commit()

    feed = HistoricalFeed(session_factory)
    results = [r async for r in feed.stream(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    )]
    assert len(results) == 1
    assert results[0][0] == _T1


async def test_stream_empty_range_yields_nothing(session_factory):
    feed = HistoricalFeed(session_factory)
    results = [r async for r in feed.stream(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 1, tzinfo=timezone.utc),
    )]
    assert results == []
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/python -m pytest tests/test_backtest/test_feed.py -v
# Expected: ImportError
```

- [ ] **Step 3: `atlas/backtest/feed.py` 구현**

```python
# atlas/backtest/feed.py
from datetime import datetime
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from atlas.db.models import RawTick


class HistoricalFeed:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def stream(
        self, start: datetime, end: datetime
    ) -> AsyncIterator[tuple[datetime, dict[str, Any]]]:
        async with self._session_factory() as session:
            result = await session.stream(
                select(RawTick)
                .where(
                    RawTick.exchange == "binance",
                    RawTick.timestamp >= start,
                    RawTick.timestamp < end,
                )
                .order_by(RawTick.timestamp, RawTick.symbol)
            )
            current_ts: datetime | None = None
            current_group: dict[str, Any] = {}

            async for tick in result.scalars():
                if current_ts is None:
                    current_ts = tick.timestamp
                if tick.timestamp != current_ts:
                    yield current_ts, current_group
                    current_group = {}
                    current_ts = tick.timestamp
                current_group[tick.symbol] = {
                    "bid": float(tick.bid),
                    "ask": float(tick.ask),
                    "last": float(tick.last),
                }

            if current_group and current_ts is not None:
                yield current_ts, current_group
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/python -m pytest tests/test_backtest/test_feed.py -v
# Expected: 3 passed
```

- [ ] **Step 5: 커밋**

```bash
git add atlas/backtest/feed.py tests/test_backtest/test_feed.py
git commit -m "feat(backtest): HistoricalFeed — async DB streaming by 1-second groups"
```

---

## Task 3: BinanceVisionFetcher

**Files:**
- Create: `atlas/backtest/fetcher.py`
- Create: `tests/test_backtest/test_fetcher.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_backtest/test_fetcher.py
import csv
import io
import zipfile
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from atlas.backtest.fetcher import BinanceVisionFetcher, _parse_zip
from atlas.db.models import Base, RawTick


def _make_zip(symbol_csv_name: str, rows: list[list]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["update_id","best_bid_price","best_bid_qty",
                         "best_ask_price","best_ask_qty","transaction_time","event_time"])
        for row in rows:
            writer.writerow(row)
        zf.writestr(symbol_csv_name, csv_buf.getvalue())
    return buf.getvalue()


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def test_parse_zip_downsamples_to_one_row_per_second():
    t_base = 1_740_787_200_000  # 2025-03-01 00:00:00 UTC in ms
    rows = [
        [1, "50000", "0.1", "50001", "0.1", t_base, t_base],
        [2, "50002", "0.1", "50003", "0.1", t_base + 100, t_base + 100],  # same second
        [3, "50100", "0.1", "50101", "0.1", t_base + 1000, t_base + 1000],  # next second
    ]
    data = _make_zip("BTCUSDT-bookTicker-2025-03-01.csv", rows)
    ticks = _parse_zip("BTC/USDT", data)

    assert len(ticks) == 2  # 2 distinct seconds
    assert ticks[0].bid == Decimal("50002")  # last row of first second wins


def test_parse_zip_skips_header_row():
    data = _make_zip("BTCUSDT-bookTicker-2025-03-01.csv", [])
    ticks = _parse_zip("BTC/USDT", data)
    assert ticks == []


def test_parse_zip_sets_exchange_and_symbol():
    t = 1_740_787_200_000
    rows = [[1, "50000", "0.1", "50001", "0.1", t, t]]
    data = _make_zip("BTCUSDT-bookTicker-2025-03-01.csv", rows)
    [tick] = _parse_zip("BTC/USDT", data)
    assert tick.exchange == "binance"
    assert tick.symbol == "BTC/USDT"


def test_parse_zip_converts_timestamp_to_utc_datetime():
    t_ms = 1_740_787_201_500  # 2025-03-01 00:00:01.500 UTC
    rows = [[1, "50000", "0.1", "50001", "0.1", t_ms, t_ms]]
    data = _make_zip("BTCUSDT-bookTicker-2025-03-01.csv", rows)
    [tick] = _parse_zip("BTC/USDT", data)
    assert tick.timestamp == datetime(2025, 3, 1, 0, 0, 1, tzinfo=timezone.utc)


async def test_fetch_inserts_rows_to_db(session_factory):
    t_ms = 1_740_787_200_000
    rows = [[1, "50000", "0.1", "50001", "0.1", t_ms, t_ms]]
    zip_data = _make_zip("BTCUSDT-bookTicker-2025-03-01.csv", rows)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_resp.raise_for_status = MagicMock()
    mock_resp.read = AsyncMock(return_value=zip_data)

    mock_http = MagicMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = MagicMock(return_value=mock_resp)

    fetcher = BinanceVisionFetcher(session_factory)
    with patch("aiohttp.ClientSession", return_value=mock_http):
        await fetcher.fetch(date(2025, 3, 1), date(2025, 3, 2))

    from sqlalchemy import select, func
    async with session_factory() as s:
        count = (await s.execute(select(func.count()).select_from(RawTick))).scalar_one()
    assert count >= 1


async def test_fetch_skips_already_fetched_dates(session_factory):
    ts = datetime(2025, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    async with session_factory() as s:
        s.add(RawTick(
            exchange="binance", symbol="BTC/USDT", timestamp=ts,
            bid=Decimal("50000"), ask=Decimal("50001"),
            last=Decimal(0), volume=Decimal(0),
        ))
        await s.commit()

    fetcher = BinanceVisionFetcher(session_factory)
    # If _already_fetched works, no HTTP call is made for BTC/USDT 2025-03-01
    download_called = []
    original = fetcher._fetch_one

    async def spy(*args, **kwargs):
        download_called.append(args[2])  # ccxt_sym
        return 0

    fetcher._fetch_one = spy
    await fetcher.fetch(date(2025, 3, 1), date(2025, 3, 2))
    assert "BTC/USDT" not in download_called


async def test_fetch_handles_404_gracefully(session_factory):
    mock_resp = MagicMock()
    mock_resp.status = 404
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_http = MagicMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = MagicMock(return_value=mock_resp)

    fetcher = BinanceVisionFetcher(session_factory)
    with patch("aiohttp.ClientSession", return_value=mock_http):
        rows = await fetcher.fetch(date(2025, 3, 1), date(2025, 3, 2))
    assert rows == 0  # no error raised
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/python -m pytest tests/test_backtest/test_fetcher.py -v
# Expected: ImportError
```

- [ ] **Step 3: `atlas/backtest/fetcher.py` 구현**

```python
# atlas/backtest/fetcher.py
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
    "ETH/BTC":  "ETHBTC",
    "BNB/USDT": "BNBUSDT",
    "BNB/BTC":  "BNBBTC",
    "BNB/ETH":  "BNBETH",
    "XRP/USDT": "XRPUSDT",
    "XRP/BTC":  "XRPBTC",
    "XRP/ETH":  "XRPETH",
}

_BASE_URL = (
    "https://data.binance.vision/data/spot/daily/bookTicker"
    "/{sym}/{sym}-bookTicker-{date}.zip"
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
        total = 0
        async with aiohttp.ClientSession() as http:
            results = await asyncio.gather(
                *[self._fetch_one(http, sem, sym, d) for sym, d in to_fetch],
                return_exceptions=True,
            )
        for r in results:
            if isinstance(r, int):
                total += r
            else:
                _log.warning("fetch error: %s", r)
        return total

    async def _fetch_one(
        self, http: aiohttp.ClientSession, sem: asyncio.Semaphore,
        ccxt_sym: str, target_date: date,
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

    async def _already_fetched(
        self, session, ccxt_sym: str, target_date: date
    ) -> bool:
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/python -m pytest tests/test_backtest/test_fetcher.py -v
# Expected: 7 passed
```

- [ ] **Step 5: 커밋**

```bash
git add atlas/backtest/fetcher.py tests/test_backtest/test_fetcher.py
git commit -m "feat(backtest): BinanceVisionFetcher — parallel download, 1s downsample, idempotent"
```

---

## Task 4: BacktestRunner + TradeRecord

**Files:**
- Create: `atlas/backtest/runner.py`
- Create: `tests/test_backtest/test_runner.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_backtest/test_runner.py
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, AsyncIterator

import pytest

from atlas.backtest.exchange import BacktestExchange
from atlas.backtest.feed import HistoricalFeed
from atlas.backtest.runner import BacktestRunner, TradeRecord
from atlas.core.exchange import Exchange
from atlas.risk.manager import RiskManager
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy

# 가격: ETH/USDT가 이론가(50000×0.06=3000) 대비 6.7% 과대평가 → 차익 기회 발생
_ARB_TICKERS = {
    "BTC/USDT": {"bid": 50000.0, "ask": 50000.0, "last": 50000.0},
    "ETH/BTC":  {"bid": 0.06,    "ask": 0.06,    "last": 0.06},
    "ETH/USDT": {"bid": 3200.0,  "ask": 3200.0,  "last": 3200.0},
}
_TS = datetime(2025, 3, 1, 0, 0, 1, tzinfo=timezone.utc)


class _StubFeed:
    """단일 ticker 스냅샷을 한 번 yield하는 스텁."""
    def __init__(self, tickers: dict[str, Any]):
        self._tickers = tickers

    async def stream(self, start: datetime, end: datetime) -> AsyncIterator:
        yield _TS, self._tickers


def _make_runner(tickers: dict, initial_usdt: str = "10000") -> BacktestRunner:
    exchange = BacktestExchange(
        initial_balance={
            "USDT": Decimal(initial_usdt),
            "BTC": Decimal("1"),
            "ETH": Decimal("100"),
            "BNB": Decimal("100"),
            "XRP": Decimal("10000"),
        },
        slippage=Decimal("0"),
    )
    feed = _StubFeed(tickers)
    strategy = TriangularArbitrageStrategy(
        exchange=Exchange.BINANCE,
        order_quantity=Decimal("0.001"),
        min_profit=Decimal("0.001"),
    )
    risk_manager = RiskManager(
        max_order_size=Decimal("10000"),
        max_exposure=Decimal("30000"),
    )
    return BacktestRunner(feed=feed, exchange=exchange, strategy=strategy, risk_manager=risk_manager)


async def test_runner_returns_list_of_trade_records():
    runner = _make_runner(_ARB_TICKERS)
    records = await runner.run(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    )
    assert isinstance(records, list)


async def test_runner_produces_trade_record_on_arbitrage():
    runner = _make_runner(_ARB_TICKERS)
    records = await runner.run(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    )
    assert len(records) >= 1


async def test_trade_record_has_required_fields():
    runner = _make_runner(_ARB_TICKERS)
    [rec] = await runner.run(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    )
    assert isinstance(rec, TradeRecord)
    assert rec.arb_id
    assert rec.status in {"COMPLETE", "UNWIND_COMPLETE", "TIMEOUT", "FAILED"}
    assert rec.timestamp == _TS
    assert rec.leg1_pair and rec.leg2_pair and rec.leg3_pair


async def test_no_signal_no_records():
    runner = _make_runner({})  # empty tickers → no prices → no signal
    records = await runner.run(
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 2, tzinfo=timezone.utc),
    )
    assert records == []
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/python -m pytest tests/test_backtest/test_runner.py -v
# Expected: ImportError
```

- [ ] **Step 3: `atlas/backtest/runner.py` 구현**

```python
# atlas/backtest/runner.py
import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from atlas.core.parsers import parse_trading_pair, to_ccxt_symbol
from atlas.core.quote import Quote
from atlas.core.trading_pair import TradingPair
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.engine import ExecutionEngine
from atlas.execution.state import ArbitrageStateMachine
from atlas.outbox.queue import OutboxEntryType, OutboxQueue
from atlas.risk.manager import RiskManager
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy

from .exchange import BacktestExchange
from .feed import HistoricalFeed


@dataclass(frozen=True, kw_only=True)
class TradeRecord:
    timestamp: datetime
    arb_id: str
    leg1_pair: str
    leg2_pair: str
    leg3_pair: str
    expected_profit: Decimal
    actual_profit: Decimal | None
    status: str


class BacktestRunner:
    def __init__(
        self,
        feed: HistoricalFeed,
        exchange: BacktestExchange,
        strategy: TriangularArbitrageStrategy,
        risk_manager: RiskManager,
    ) -> None:
        self._feed = feed
        self._exchange = exchange
        self._strategy = strategy
        self._outbox: OutboxQueue = asyncio.Queue()
        state_machine = ArbitrageStateMachine(exchange=exchange, outbox=self._outbox)
        self._engine = ExecutionEngine(risk_manager=risk_manager, state_machine=state_machine)
        self._records: list[TradeRecord] = []

    async def run(self, start: datetime, end: datetime) -> list[TradeRecord]:
        async for ts, tickers in self._feed.stream(start, end):
            self._exchange.update_prices(tickers)
            self._engine.update_prices(_extract_usdt_prices(tickers))
            signals = self._strategy.on_tickers(tickers)
            for signal in signals:
                await self._engine.on_signal(signal)
                self._drain_outbox(ts, signal)
        return self._records

    def _drain_outbox(self, ts: datetime, signal: ArbSignal) -> None:
        while not self._outbox.empty():
            entry = self._outbox.get_nowait()
            if entry.entry_type != OutboxEntryType.TRADE_RESULT:
                continue
            p = entry.payload
            net_pnl = Decimal(p["net_pnl"]) if p.get("net_pnl") else None
            self._records.append(TradeRecord(
                timestamp=ts,
                arb_id=p["arb_id"],
                leg1_pair=to_ccxt_symbol(signal.leg1_pair),
                leg2_pair=to_ccxt_symbol(signal.leg2_pair),
                leg3_pair=to_ccxt_symbol(signal.leg3_pair),
                expected_profit=signal.expected_profit,
                actual_profit=net_pnl,
                status=p["state"],
            ))


def _extract_usdt_prices(tickers: dict[str, Any]) -> dict[TradingPair, Decimal]:
    out: dict[TradingPair, Decimal] = {}
    for symbol, data in tickers.items():
        try:
            pair = parse_trading_pair(symbol)
        except (ValueError, KeyError):
            continue
        if pair.quote != Quote.USDT:
            continue
        last = data.get("last") or 0
        bid = data.get("bid") or last
        ask = data.get("ask") or last
        if bid and ask:
            mid = (Decimal(str(bid)) + Decimal(str(ask))) / Decimal("2")
            out[pair] = mid
    return out
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/python -m pytest tests/test_backtest/test_runner.py -v
# Expected: 4 passed
```

- [ ] **Step 5: 커밋**

```bash
git add atlas/backtest/runner.py tests/test_backtest/test_runner.py
git commit -m "feat(backtest): BacktestRunner wires strategy/engine/exchange, collects TradeRecords"
```

---

## Task 5: BacktestReport

**Files:**
- Create: `atlas/backtest/report.py`

(별도 단위 테스트 없음 — Task 6의 통합 확인으로 검증)

- [ ] **Step 1: `atlas/backtest/report.py` 구현**

```python
# atlas/backtest/report.py
import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .runner import TradeRecord


@dataclass
class BacktestSummary:
    start: datetime
    end: datetime
    initial_balance: Decimal
    final_balance: Decimal
    records: list[TradeRecord]

    def print_summary(self) -> None:
        pnl = self.final_balance - self.initial_balance
        pnl_pct = (pnl / self.initial_balance * 100) if self.initial_balance else Decimal(0)

        completed = [r for r in self.records if r.status == "COMPLETE"]
        unwind = sum(1 for r in self.records if r.status == "UNWIND_COMPLETE")
        timeout = sum(1 for r in self.records if r.status == "TIMEOUT")
        win_rate = len(completed) / len(self.records) * 100 if self.records else 0.0

        profits = [r.actual_profit for r in completed if r.actual_profit is not None]
        avg_pnl = sum(profits) / len(profits) if profits else Decimal(0)

        running = Decimal(0)
        peak = Decimal(0)
        max_dd = Decimal(0)
        for r in self.records:
            if r.actual_profit:
                running += r.actual_profit
                if running > peak:
                    peak = running
                dd = peak - running
                if dd > max_dd:
                    max_dd = dd

        print(f"\n{'=' * 48}")
        print(f"Backtest: {self.start.date()} → {self.end.date()}")
        print(f"{'=' * 48}")
        print(f"초기 잔고:    {self.initial_balance:.2f} USDT")
        print(f"최종 잔고:    {self.final_balance:.2f} USDT")
        print(f"총 PnL:      {pnl:+.4f} USDT  ({pnl_pct:+.2f}%)")
        print(f"거래 수:      {len(self.records)}"
              f"  (COMPLETE {len(completed)} / UNWIND {unwind} / TIMEOUT {timeout})")
        print(f"승률:         {win_rate:.1f}%")
        print(f"평균 수익:   {avg_pnl:+.6f} USDT/거래")
        print(f"최대 낙폭:   -{max_dd:.4f} USDT")
        print(f"{'=' * 48}\n")

    def to_csv(self, path: str) -> None:
        fields = [
            "timestamp", "arb_id", "leg1_pair", "leg2_pair", "leg3_pair",
            "expected_profit", "actual_profit", "status",
        ]
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in self.records:
                w.writerow({
                    "timestamp": r.timestamp.isoformat(),
                    "arb_id": r.arb_id,
                    "leg1_pair": r.leg1_pair,
                    "leg2_pair": r.leg2_pair,
                    "leg3_pair": r.leg3_pair,
                    "expected_profit": str(r.expected_profit),
                    "actual_profit": str(r.actual_profit) if r.actual_profit is not None else "",
                    "status": r.status,
                })
        print(f"결과 저장됨: {path}")
```

- [ ] **Step 2: 커밋**

```bash
git add atlas/backtest/report.py
git commit -m "feat(backtest): BacktestSummary — terminal output and CSV export"
```

---

## Task 6: CLI — run_backtest.py

**Files:**
- Create: `run_backtest.py`

- [ ] **Step 1: `run_backtest.py` 구현**

```python
# run_backtest.py
"""
백테스트 CLI.

환경 변수:
  DATABASE_URL  PostgreSQL 연결 문자열 (필수)

예시:
  # 데이터 취득 + 실행 한 번에
  DATABASE_URL=postgresql+asyncpg://... python run_backtest.py \\
    --start 2025-03-01 --end 2025-05-31 --fetch --output results.csv

  # 이미 DB에 데이터 있을 때
  DATABASE_URL=... python run_backtest.py \\
    --start 2025-03-01 --end 2025-05-31 --qty 0.001
"""
import argparse
import asyncio
import logging
import os
from datetime import date, datetime, timezone
from decimal import Decimal

from atlas.backtest.exchange import BacktestExchange
from atlas.backtest.feed import HistoricalFeed
from atlas.backtest.fetcher import BinanceVisionFetcher
from atlas.backtest.report import BacktestSummary
from atlas.backtest.runner import BacktestRunner
from atlas.core.exchange import Exchange
from atlas.db.connection import create_engine, create_session_factory
from atlas.risk.manager import RiskManager
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Atlas triangular arbitrage backtest")
    p.add_argument("--start",           required=True, help="Start date YYYY-MM-DD (inclusive)")
    p.add_argument("--end",             required=True, help="End date YYYY-MM-DD (exclusive)")
    p.add_argument("--fetch",           action="store_true", help="Download data before running")
    p.add_argument("--qty",             default="0.001",  help="Leg-1 order quantity (default: 0.001 BTC)")
    p.add_argument("--initial-balance", default="1000",   help="Starting USDT balance (default: 1000)")
    p.add_argument("--min-profit",      default="0.002",  help="Min profit threshold (default: 0.2%%)")
    p.add_argument("--output",          default="",       help="CSV output path (optional)")
    return p.parse_args()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()

    database_url = os.environ["DATABASE_URL"]
    session_factory = create_session_factory(create_engine(database_url))

    start_date = date.fromisoformat(args.start)
    end_date   = date.fromisoformat(args.end)
    start_dt   = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    end_dt     = datetime(end_date.year,   end_date.month,   end_date.day,   tzinfo=timezone.utc)

    if args.fetch:
        print(f"[FETCH] {start_date} ~ {end_date} 데이터 취득 중…")
        fetcher = BinanceVisionFetcher(session_factory)
        inserted = await fetcher.fetch(start_date, end_date)
        print(f"[FETCH] {inserted:,}행 적재 완료")

    initial_usdt = Decimal(args.initial_balance)
    exchange = BacktestExchange(
        initial_balance={
            "USDT": initial_usdt,
            "BTC":  Decimal("0"),
            "ETH":  Decimal("0"),
            "BNB":  Decimal("0"),
            "XRP":  Decimal("0"),
        },
    )
    feed     = HistoricalFeed(session_factory)
    strategy = TriangularArbitrageStrategy(
        exchange=Exchange.BINANCE,
        order_quantity=Decimal(args.qty),
        min_profit=Decimal(args.min_profit),
    )
    risk_manager = RiskManager(
        max_order_size=initial_usdt,
        max_exposure=initial_usdt * 3,
    )
    runner = BacktestRunner(
        feed=feed, exchange=exchange, strategy=strategy, risk_manager=risk_manager
    )

    print(f"[RUN] {start_dt.date()} ~ {end_dt.date()} 백테스트 실행 중…")
    records = await runner.run(start_dt, end_dt)

    BacktestSummary(
        start=start_dt,
        end=end_dt,
        initial_balance=initial_usdt,
        final_balance=exchange.get_usdt_balance(),
        records=records,
    ).print_summary()

    if args.output:
        BacktestSummary(
            start=start_dt, end=end_dt,
            initial_balance=initial_usdt,
            final_balance=exchange.get_usdt_balance(),
            records=records,
        ).to_csv(args.output)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 전체 테스트 통과 확인**

```bash
.venv/bin/python -m pytest tests/ -q
# Expected: 모든 테스트 통과 (기존 148 + 신규 ~18 ≈ 166+)
```

- [ ] **Step 3: import 확인 (DB 없이)**

```bash
.venv/bin/python -c "from atlas.backtest.runner import BacktestRunner; print('OK')"
# Expected: OK
```

- [ ] **Step 4: 커밋**

```bash
git add run_backtest.py
git commit -m "feat(backtest): run_backtest.py CLI — fetch + backtest in one command"
```

---

## 완료 기준

- [ ] `pytest tests/test_backtest/ -v` — 전체 통과
- [ ] `python run_backtest.py --start 2025-03-01 --end 2025-03-02 --fetch` — 데이터 취득 성공
- [ ] `python run_backtest.py --start 2025-03-01 --end 2025-03-02` — 터미널 요약 출력
- [ ] `--output results.csv` 옵션으로 CSV 파일 생성 확인
