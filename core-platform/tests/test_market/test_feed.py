import asyncio
from decimal import Decimal

import pytest

from atlas.core.exchange import Exchange
from atlas.events.bus import EventBus
from atlas.events.market_data_event import MarketDataEvent
from atlas.exchange.ccxt_ticker import CcxtTicker
from atlas.market.feed import MarketDataFeed
from atlas.market.tick import Tick

_BTC_TICKER = CcxtTicker(
    symbol="BTC/USDT",
    timestamp=1717459200000,
    bid=67000.0,
    ask=67001.0,
    last=67000.5,
    base_volume=1500.0,
)
_ETH_TICKER = CcxtTicker(
    symbol="ETH/USDT",
    timestamp=1717459200001,
    bid=3500.0,
    ask=3501.0,
    last=3500.5,
    base_volume=5000.0,
)


@pytest.mark.asyncio
async def test_on_tickers_publishes_market_data_event():
    bus = EventBus()
    outbox = asyncio.Queue()
    feed = MarketDataFeed(exchange=Exchange.BINANCE, bus=bus, outbox=outbox)

    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(MarketDataEvent, handler)

    await feed.on_tickers({"BTC/USDT": _BTC_TICKER})

    assert len(received) == 1
    event = received[0]
    assert isinstance(event, MarketDataEvent)
    assert event.bid == Decimal("67000.0")
    assert event.ask == Decimal("67001.0")
    assert event.last == Decimal("67000.5")
    assert event.exchange == Exchange.BINANCE


@pytest.mark.asyncio
async def test_on_tickers_puts_tick_to_outbox():
    bus = EventBus()
    outbox = asyncio.Queue()
    feed = MarketDataFeed(exchange=Exchange.BINANCE, bus=bus, outbox=outbox)

    await feed.on_tickers({"BTC/USDT": _BTC_TICKER})

    assert outbox.qsize() == 1
    tick = outbox.get_nowait()
    assert isinstance(tick, Tick)
    assert tick.timestamp == 1717459200000
    assert tick.volume == Decimal("1500.0")


@pytest.mark.asyncio
async def test_on_tickers_multiple_symbols():
    bus = EventBus()
    outbox = asyncio.Queue()
    feed = MarketDataFeed(exchange=Exchange.BINANCE, bus=bus, outbox=outbox)

    await feed.on_tickers({"BTC/USDT": _BTC_TICKER, "ETH/USDT": _ETH_TICKER})

    assert outbox.qsize() == 2
