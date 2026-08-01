from decimal import Decimal

from kalshi_bot.fees import taker_fee


def test_fee_peaks_at_half_and_rounds_up():
    assert taker_fee(price=Decimal("0.50"), count=Decimal(1)) == Decimal("0.02")


def test_fee_exact_at_hundred_contracts():
    assert taker_fee(price=Decimal("0.50"), count=Decimal(100)) == Decimal("1.75")


def test_fee_rounds_up_partial_cent():
    assert taker_fee(price=Decimal("0.50"), count=Decimal(10)) == Decimal("0.18")


def test_fee_minimum_one_cent_at_extreme_price():
    assert taker_fee(price=Decimal("0.01"), count=Decimal(1)) == Decimal("0.01")


def test_fee_custom_coefficient():
    fee = taker_fee(price=Decimal("0.50"), count=Decimal(100), coef=Decimal("0.0175"))
    assert fee == Decimal("0.44")
