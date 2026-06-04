from decimal import Decimal

import pytest

from atlas.core.exchange import Exchange
from atlas.core.parsers import parse_trading_pair
from atlas.events.bus import EventBus
from atlas.events.market_data_event import MarketDataEvent
from atlas.events.signal_event import SignalEvent


@pytest.mark.asyncio
async def test_subscribe_and_receive_event():
    bus = EventBus()
    received = []

    async def handler(event: MarketDataEvent):
        received.append(event)

    bus.subscribe(MarketDataEvent, handler)
    event = MarketDataEvent(
        exchange=Exchange.BINANCE,
        trading_pair=parse_trading_pair("BTC/USDT"),
        bid=Decimal("50000"),
        ask=Decimal("50001"),
        last=Decimal("50000"),
    )
    await bus.publish(event)

    assert len(received) == 1
    assert received[0].trading_pair.ticker == "BTC"


@pytest.mark.asyncio
async def test_multiple_subscribers_receive_same_event():
    bus = EventBus()
    results = []

    async def handler_a(e):
        results.append("a")

    async def handler_b(e):
        results.append("b")

    bus.subscribe(MarketDataEvent, handler_a)
    bus.subscribe(MarketDataEvent, handler_b)
    await bus.publish(
        MarketDataEvent(
            exchange=Exchange.BINANCE,
            trading_pair=parse_trading_pair("ETH/USDT"),
            bid=Decimal("3000"),
            ask=Decimal("3001"),
            last=Decimal("3000"),
        )
    )

    assert sorted(results) == ["a", "b"]


@pytest.mark.asyncio
async def test_handler_exception_does_not_block_other_handlers():
    # M-7: a buggy subscriber must not block the rest of the fan-out.
    bus = EventBus()
    received = []

    async def bad_handler(e):
        raise RuntimeError("boom")

    async def good_handler(e):
        received.append("ok")

    bus.subscribe(MarketDataEvent, bad_handler)
    bus.subscribe(MarketDataEvent, good_handler)
    await bus.publish(
        MarketDataEvent(
            exchange=Exchange.BINANCE,
            trading_pair=parse_trading_pair("BTC/USDT"),
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000"),
        )
    )

    assert received == ["ok"]


@pytest.mark.asyncio
async def test_unsubscribed_type_not_received():
    bus = EventBus()
    received = []

    async def handler(e):
        received.append(e)

    bus.subscribe(SignalEvent, handler)
    await bus.publish(
        MarketDataEvent(
            exchange=Exchange.BINANCE,
            trading_pair=parse_trading_pair("BTC/USDT"),
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000"),
        )
    )

    assert received == []
