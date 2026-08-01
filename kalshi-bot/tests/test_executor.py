import dataclasses
from decimal import Decimal
from pathlib import Path

from kalshi_bot.executor import BasketExecutor
from kalshi_bot.models import (
    Opportunity,
    OpportunityKind,
    OpportunityLeg,
    OrderRequest,
    OrderResult,
)
from kalshi_bot.store import Store
from tests.conftest import make_quote


class FakeTrading:
    def __init__(self, fills_by_ticker: dict[str, list[Decimal]]) -> None:
        self._fills = fills_by_ticker
        self.requests: list[OrderRequest] = []

    async def create_order(self, request: OrderRequest) -> OrderResult:
        self.requests.append(request)
        fill = self._fills.get(request.ticker, [Decimal(0)]).pop(0)
        return OrderResult(
            order_id=f"ord-{len(self.requests)}",
            client_order_id=request.client_order_id,
            fill_count=fill,
            remaining_count=request.count - fill,
            average_fill_price=request.price if fill > 0 else None,
            average_fee_paid=None,
        )


class FakePublic:
    def __init__(self, quotes: dict) -> None:
        self._quotes = quotes

    async def get_market(self, ticker: str):
        return self._quotes.get(ticker)


def make_no_basket(count: str = "10") -> Opportunity:
    legs = (
        OpportunityLeg(
            ticker="EVT-0", side="no", price=Decimal("0.60"), available_size=Decimal(50)
        ),
        OpportunityLeg(
            ticker="EVT-1", side="no", price=Decimal("0.60"), available_size=Decimal(50)
        ),
    )
    return Opportunity(
        kind=OpportunityKind.NO_BASKET,
        event_ticker="EVT",
        legs=legs,
        count=Decimal(count),
        gross_edge_total=Decimal("2.00"),
        fee_total=Decimal("0.34"),
        net_edge_total=Decimal("1.66"),
        executable=True,
    )


def make_executor(tmp_path: Path, trading, public) -> tuple[BasketExecutor, Store]:
    store = Store(tmp_path / "test.sqlite3")
    executor = BasketExecutor(
        trading=trading,
        public=public,
        store=store,
        max_total_exposure=Decimal("100"),
    )
    return executor, store


def good_quotes() -> dict:
    return {
        ticker: make_quote(ticker=ticker, yes_bid="0.40", yes_ask="0.45")
        for ticker in ("EVT-0", "EVT-1")
    }


async def test_full_fill_returns_true(tmp_path):
    trading = FakeTrading({"EVT-0": [Decimal(10)], "EVT-1": [Decimal(10)]})
    executor, store = make_executor(tmp_path, trading, FakePublic(good_quotes()))

    assert await executor.execute(make_no_basket(), opportunity_id=1)

    assert len(trading.requests) == 2
    assert all(r.side == "ask" and r.price == Decimal("0.40") for r in trading.requests)
    assert all(r.time_in_force == "immediate_or_cancel" for r in trading.requests)
    store.close()


async def test_partial_fill_retries_then_unwinds_excess(tmp_path):
    trading = FakeTrading(
        {"EVT-0": [Decimal(10), Decimal(3)], "EVT-1": [Decimal(4), Decimal(0)]}
    )
    executor, store = make_executor(tmp_path, trading, FakePublic(good_quotes()))

    assert not await executor.execute(make_no_basket(), opportunity_id=1)

    # entry ×2, EVT-1 재시도 ×1, EVT-0 초과분(10−4=6) 언와인드 ×1
    retry = [r for r in trading.requests if r.ticker == "EVT-1"][1]
    assert retry.count == Decimal(6)
    unwind = trading.requests[-1]
    assert unwind.ticker == "EVT-0"
    assert unwind.side == "bid"
    assert unwind.price == Decimal("0.45")
    assert unwind.count == Decimal(6)
    store.close()


async def test_requote_failure_aborts_without_orders(tmp_path):
    worse_quotes = {
        ticker: make_quote(ticker=ticker, yes_bid="0.30", yes_ask="0.45")
        for ticker in ("EVT-0", "EVT-1")
    }
    trading = FakeTrading({})
    executor, store = make_executor(tmp_path, trading, FakePublic(worse_quotes))

    assert not await executor.execute(make_no_basket(), opportunity_id=1)

    assert trading.requests == []
    store.close()


async def test_exposure_limit_blocks_execution(tmp_path):
    trading = FakeTrading({"EVT-0": [Decimal(10)], "EVT-1": [Decimal(10)]})
    store = Store(tmp_path / "test.sqlite3")
    executor = BasketExecutor(
        trading=trading,
        public=FakePublic(good_quotes()),
        store=store,
        max_total_exposure=Decimal("1"),
    )

    assert not await executor.execute(make_no_basket(), opportunity_id=1)
    assert trading.requests == []
    store.close()


async def test_non_executable_opportunity_rejected(tmp_path):
    trading = FakeTrading({})
    executor, store = make_executor(tmp_path, trading, FakePublic(good_quotes()))
    anomaly = dataclasses.replace(
        make_no_basket(), kind=OpportunityKind.YES_SUM_ANOMALY, executable=False
    )

    assert not await executor.execute(anomaly, opportunity_id=1)
    assert trading.requests == []
    store.close()
