import asyncio
from decimal import Decimal

import pytest

from atlas.core.exchange import Exchange
from atlas.market.feed import MarketDataFeed
from atlas.market.tick import Tick

_BTC_RAW = {
    "timestamp": 1717459200000,
    "bid": 67000.0,
    "ask": 67001.0,
    "last": 67000.5,
    "baseVolume": 1500.0,
}
_ETH_RAW = {
    "timestamp": 1717459200001,
    "bid": 3500.0,
    "ask": 3501.0,
    "last": 3500.5,
    "baseVolume": 5000.0,
}


@pytest.mark.asyncio
async def test_on_tickers_puts_tick_to_queue():
    tick_queue: asyncio.Queue = asyncio.Queue()
    feed = MarketDataFeed(exchange=Exchange.BINANCE, tick_queue=tick_queue)

    await feed.on_tickers({"BTC/USDT": _BTC_RAW})

    assert tick_queue.qsize() == 1
    tick = tick_queue.get_nowait()
    assert isinstance(tick, Tick)
    assert tick.timestamp == 1717459200000
    assert tick.volume == Decimal("1500.0")


@pytest.mark.asyncio
async def test_on_tickers_multiple_symbols():
    tick_queue: asyncio.Queue = asyncio.Queue()
    feed = MarketDataFeed(exchange=Exchange.BINANCE, tick_queue=tick_queue)

    await feed.on_tickers({"BTC/USDT": _BTC_RAW, "ETH/USDT": _ETH_RAW})

    assert tick_queue.qsize() == 2


@pytest.mark.asyncio
async def test_on_tickers_drops_ticks_without_timestamp():
    # M-8: ticks with missing/zero timestamp must be dropped.
    tick_queue: asyncio.Queue = asyncio.Queue()
    feed = MarketDataFeed(exchange=Exchange.BINANCE, tick_queue=tick_queue)

    bad = {**_BTC_RAW, "timestamp": None}
    await feed.on_tickers({"BTC/USDT": bad})
    assert tick_queue.qsize() == 0

    bad_zero = {**_BTC_RAW, "timestamp": 0}
    await feed.on_tickers({"BTC/USDT": bad_zero})
    assert tick_queue.qsize() == 0
