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

_T_BASE_US = 1_740_787_200_000_000  # 2025-03-01 00:00:00 UTC in µs


def _kline(open_time: int, close: str, volume: str = "0.5") -> list:
    return [
        open_time,
        close,
        close,
        close,
        close,
        volume,
        open_time + 999_999,
        "0",
        1,
        "0",
        "0",
        0,
    ]


def _make_zip(csv_name: str, rows: list[list]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
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


def test_parse_zip_keeps_last_row_per_second():
    rows = [
        _kline(_T_BASE_US, "50000"),
        _kline(_T_BASE_US + 100_000, "50002"),  # same second
        _kline(_T_BASE_US + 1_000_000, "50100"),  # next second
    ]
    data = _make_zip("BTCUSDT-1s-2025-03-01.csv", rows)
    ticks = _parse_zip("BTC/USDT", data)
    assert len(ticks) == 2
    assert ticks[0].bid == Decimal("50002")


def test_parse_zip_handles_pre2025_ms_timestamps():
    t_ms = 1_704_067_200_000  # 2024-01-01 00:00:00 UTC in ms
    data = _make_zip("BTCUSDT-1s-2024-01-01.csv", [_kline(t_ms, "42000")])
    [tick] = _parse_zip("BTC/USDT", data)
    assert tick.timestamp == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_parse_zip_empty_csv_returns_nothing():
    data = _make_zip("BTCUSDT-1s-2025-03-01.csv", [])
    ticks = _parse_zip("BTC/USDT", data)
    assert ticks == []


def test_parse_zip_sets_exchange_and_symbol():
    data = _make_zip("BTCUSDT-1s-2025-03-01.csv", [_kline(_T_BASE_US, "50000")])
    [tick] = _parse_zip("BTC/USDT", data)
    assert tick.exchange == "binance"
    assert tick.symbol == "BTC/USDT"


def test_parse_zip_converts_us_timestamp_to_utc_datetime():
    t_us = _T_BASE_US + 1_500_000  # 00:00:01.500 → second=1
    data = _make_zip("BTCUSDT-1s-2025-03-01.csv", [_kline(t_us, "50000")])
    [tick] = _parse_zip("BTC/USDT", data)
    assert tick.timestamp == datetime(2025, 3, 1, 0, 0, 1, tzinfo=timezone.utc)


def test_parse_zip_uses_close_as_bid_ask_last():
    data = _make_zip("BTCUSDT-1s-2025-03-01.csv", [_kline(_T_BASE_US, "50000", volume="1.25")])
    [tick] = _parse_zip("BTC/USDT", data)
    assert tick.bid == Decimal("50000")
    assert tick.ask == Decimal("50000")
    assert tick.last == Decimal("50000")
    assert tick.volume == Decimal("1.25")


async def test_fetch_inserts_rows_to_db(session_factory):
    zip_data = _make_zip("BTCUSDT-1s-2025-03-01.csv", [_kline(_T_BASE_US, "50000")])

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
