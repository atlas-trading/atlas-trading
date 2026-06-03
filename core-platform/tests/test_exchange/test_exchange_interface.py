import pytest

from atlas.exchange.exchange_interface import ExchangeInterface


def _make_mock() -> ExchangeInterface:
    class MockExchange(ExchangeInterface):
        async def place_order(self, order):
            return order

        async def cancel_order(self, order_id):
            pass

        async def get_balance(self):
            return {"USDT": 1000}

        async def health_check(self):
            return True

        async def subscribe_ticker(self, trading_pairs, callback):
            pass

        async def close(self):
            pass

    return MockExchange()


def test_exchange_interface_is_abstract():
    with pytest.raises(TypeError):
        ExchangeInterface()


def test_mock_exchange_implements_interface():
    ex = _make_mock()
    assert isinstance(ex, ExchangeInterface)


@pytest.mark.asyncio
async def test_health_check_returns_bool():
    result = await _make_mock().health_check()
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_get_balance_returns_dict():
    balance = await _make_mock().get_balance()
    assert isinstance(balance, dict)
    assert "USDT" in balance
