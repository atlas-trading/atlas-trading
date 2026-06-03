import pytest

from atlas.exchange.binance import BinanceAdapter
from atlas.exchange.exchange_interface import ExchangeInterface


def test_binance_adapter_implements_interface():
    adapter = BinanceAdapter(api_key="test", api_secret="test")
    assert isinstance(adapter, ExchangeInterface)


@pytest.mark.asyncio
async def test_on_ticker_calls_callback():
    adapter = BinanceAdapter(api_key="test", api_secret="test")
    received = []

    async def callback(tickers):
        received.append(tickers)

    await adapter._on_ticker(
        {"BTC/USDT": {"bid": 50000.0, "ask": 50001.0, "last": 50000.5}},
        callback,
    )

    assert len(received) == 1
    assert received[0]["BTC/USDT"]["bid"] == 50000.0
