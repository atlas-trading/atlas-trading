import os

import pytest

from atlas.exchange.binance import BinanceAdapter
from atlas.exchange.exchange_interface import ExchangeInterface

_TESTNET_KEY = os.getenv("BINANCE_TESTNET_API_KEY", "")
_TESTNET_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET", "")
requires_testnet = pytest.mark.skipif(not _TESTNET_KEY, reason="testnet keys not set")


def test_binance_adapter_implements_interface():
    adapter = BinanceAdapter(api_key="test", api_secret="test")
    assert isinstance(adapter, ExchangeInterface)


@pytest.mark.asyncio
async def test_on_ticker_calls_callback():
    adapter = BinanceAdapter(api_key="test", api_secret="test")
    received = []

    async def callback(tickers: dict):
        received.append(tickers)

    await adapter._on_ticker(
        {"BTC/USDT": {"bid": 50000.0, "ask": 50001.0, "last": 50000.5}},
        callback,
    )

    assert len(received) == 1
    assert received[0]["BTC/USDT"]["bid"] == 50000.0


@requires_testnet
@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check_testnet():
    adapter = BinanceAdapter(api_key=_TESTNET_KEY, api_secret=_TESTNET_SECRET, testnet=True)
    try:
        result: bool = await adapter.health_check()
        assert result is True
    finally:
        await adapter.close()


@requires_testnet
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_balance_testnet():
    adapter = BinanceAdapter(api_key=_TESTNET_KEY, api_secret=_TESTNET_SECRET, testnet=True)
    try:
        balance: dict = await adapter.get_balance()
        assert isinstance(balance, dict)
    finally:
        await adapter.close()
