from decimal import ROUND_CEILING, Decimal

TAKER_FEE_COEF = Decimal("0.07")
CENT = Decimal("0.01")


def taker_fee(*, price: Decimal, count: Decimal, coef: Decimal = TAKER_FEE_COEF) -> Decimal:
    """Kalshi 수수료: ceil_to_cent(coef × C × P × (1−P)). 주문 단위로 올림."""
    raw = coef * count * price * (Decimal(1) - price)
    return raw.quantize(CENT, rounding=ROUND_CEILING)
