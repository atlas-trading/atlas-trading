from decimal import Decimal

from kalshi_bot.models import EventSnapshot, OpportunityKind
from kalshi_bot.scanner import detect
from tests.conftest import make_quote


def make_event(markets, *, mutually_exclusive=True) -> EventSnapshot:
    return EventSnapshot(
        event_ticker="EVT",
        title="test event",
        mutually_exclusive=mutually_exclusive,
        markets=tuple(markets),
    )


def test_no_basket_detected(config):
    markets = [
        make_quote(ticker=f"EVT-{i}", yes_bid="0.40", yes_ask="0.45") for i in range(3)
    ]
    opportunities = detect(make_event(markets), config)
    basket = next(o for o in opportunities if o.kind == OpportunityKind.NO_BASKET)
    assert basket.count == Decimal(10)
    assert all(leg.side == "no" and leg.price == Decimal("0.60") for leg in basket.legs)
    # gross = (2 − 1.80) × 10 = 2.00, fee = ceil(0.07×10×0.6×0.4)=0.17 × 3legs = 0.51
    assert basket.gross_edge_total == Decimal("2.00")
    assert basket.fee_total == Decimal("0.51")
    assert basket.net_edge_total == Decimal("1.49")
    assert basket.executable


def test_no_basket_requires_mutual_exclusivity(config):
    markets = [
        make_quote(ticker=f"EVT-{i}", yes_bid="0.40", yes_ask="0.45") for i in range(3)
    ]
    opportunities = detect(make_event(markets, mutually_exclusive=False), config)
    assert all(o.kind != OpportunityKind.NO_BASKET for o in opportunities)


def test_no_basket_rejected_when_fees_eat_edge(config):
    markets = [
        make_quote(ticker=f"EVT-{i}", yes_bid="0.35", yes_ask="0.40") for i in range(3)
    ]
    opportunities = detect(make_event(markets), config)
    assert all(o.kind != OpportunityKind.NO_BASKET for o in opportunities)


def test_no_basket_skipped_when_a_leg_has_no_bid(config):
    markets = [
        make_quote(ticker="EVT-0", yes_bid="0.40", yes_ask="0.45"),
        make_quote(ticker="EVT-1", yes_bid="0", yes_ask="0.45", yes_bid_size="0"),
    ]
    opportunities = detect(make_event(markets), config)
    assert all(o.kind != OpportunityKind.NO_BASKET for o in opportunities)


def test_yes_sum_anomaly_recorded_but_not_executable(config):
    markets = [
        make_quote(ticker=f"EVT-{i}", yes_bid="0.25", yes_ask="0.30") for i in range(3)
    ]
    opportunities = detect(make_event(markets), config)
    anomaly = next(o for o in opportunities if o.kind == OpportunityKind.YES_SUM_ANOMALY)
    assert not anomaly.executable
    assert anomaly.gross_edge_total == Decimal("1.00")


def test_single_market_complement_on_crossed_book(config):
    market = make_quote(ticker="EVT-X", yes_bid="0.65", yes_ask="0.40")
    opportunities = detect(make_event([market], mutually_exclusive=False), config)
    single = next(
        o for o in opportunities if o.kind == OpportunityKind.SINGLE_MARKET_COMPLEMENT
    )
    assert single.executable
    # yes_ask 0.40 + no_ask 0.35 = 0.75 → gross 0.25/contract
    assert single.gross_edge_total == Decimal("2.50")


def test_inactive_markets_ignored(config):
    markets = [
        make_quote(ticker=f"EVT-{i}", yes_bid="0.40", yes_ask="0.45", status="closed")
        for i in range(3)
    ]
    assert detect(make_event(markets), config) == []
