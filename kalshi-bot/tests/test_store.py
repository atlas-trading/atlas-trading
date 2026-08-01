from decimal import Decimal

from kalshi_bot.models import (
    Opportunity,
    OpportunityKind,
    OpportunityLeg,
    OrderResult,
)
from kalshi_bot.store import Store


def make_opportunity() -> Opportunity:
    return Opportunity(
        kind=OpportunityKind.NO_BASKET,
        event_ticker="EVT",
        legs=(
            OpportunityLeg(
                ticker="EVT-0", side="no", price=Decimal("0.60"),
                available_size=Decimal(50),
            ),
        ),
        count=Decimal(10),
        gross_edge_total=Decimal("2.00"),
        fee_total=Decimal("0.17"),
        net_edge_total=Decimal("1.83"),
        executable=True,
    )


def test_opportunity_roundtrip(tmp_path):
    store = Store(tmp_path / "t.sqlite3")
    opportunity_id = store.record_opportunity(make_opportunity())
    assert opportunity_id > 0
    store.close()


def test_total_filled_cost_counts_entry_and_retry_only(tmp_path):
    store = Store(tmp_path / "t.sqlite3")

    def result(fill: str, price: str) -> OrderResult:
        return OrderResult(
            order_id="o1",
            client_order_id="c1",
            fill_count=Decimal(fill),
            remaining_count=Decimal(0),
            average_fill_price=Decimal(price),
            average_fee_paid=None,
        )

    common = {"opportunity_id": 1, "ticker": "EVT-0", "side": "ask",
              "price": Decimal("0.40"), "count": Decimal(10)}
    store.record_order(**common, purpose="entry", result=result("10", "0.40"))
    store.record_order(**common, purpose="retry", result=result("5", "0.40"))
    store.record_order(**common, purpose="unwind", result=result("5", "0.45"))
    store.record_order(**common, purpose="entry", error="rejected")

    assert store.total_filled_cost() == Decimal("6.00")
    store.close()
