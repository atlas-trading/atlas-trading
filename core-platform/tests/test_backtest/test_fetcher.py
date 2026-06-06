import csv
import io
import zipfile
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from atlas.backtest.fetcher import BinanceVisionFetcher, _parse_zip
from atlas.db.models import Base, RawTick


def _make_zip(csv_name: str, rows: list[list]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(
            [
                "update_id",
                "best_bid_price",
                "best_bid_qty",
                "best_ask_price",
                "best_ask_qty",
                "transaction_time",
                "event_time",
            ]
        )
        for row in rows:
            writer.writerow(row)
        zf.writestr(csv_name, csv_buf.getvalue())
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
    t_ms = 1_740_787_201_500  # 2025-03-01 00:00:01.500 UTC → second=1
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

    from sqlalchemy import func, select

    async with session_factory() as s:
        count = (await s.execute(select(func.count()).select_from(RawTick))).scalar_one()
    assert count >= 1


async def test_fetch_skips_already_fetched_dates(session_factory):
    ts = datetime(2025, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    async with session_factory() as s:
        s.add(
            RawTick(
                exchange="binance",
                symbol="BTC/USDT",
                timestamp=ts,
                bid=Decimal("50000"),
                ask=Decimal("50001"),
                last=Decimal(0),
                volume=Decimal(0),
            )
        )
        await s.commit()

    fetcher = BinanceVisionFetcher(session_factory)
    download_called = []

    async def spy(http, sem, ccxt_sym, d):
        download_called.append(ccxt_sym)
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
    assert rows == 0
