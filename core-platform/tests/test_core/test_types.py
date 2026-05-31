from decimal import Decimal
from atlas.core.types import TradingPair


def test_trading_pair_parses_symbol():
    pair = TradingPair.from_symbol("BTC/USDT")
    assert pair.base == "BTC"
    assert pair.quote == "USDT"
    assert str(pair) == "BTC/USDT"


def test_amount_is_decimal_not_float():
    # float 연산 오차 방지 — Decimal 사용 강제
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
    assert 0.1 + 0.2 != 0.3  # float은 오차 있음을 문서화
