"""
Regression tests: ArbitrageStateMachine → OutboxQueue 연동 (Bug 1 fix)

상태 머신의 터미널 상태(COMPLETE, UNWIND_COMPLETE, TIMEOUT, FAILED)마다
OutboxQueue에 TRADE_RESULT 항목이 enqueue되는지 검증한다.
"""

import asyncio
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.exchange.order_result import OrderResult
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.order import Order
from atlas.execution.order_status import OrderStatus
from atlas.execution.side import Side
from atlas.execution.state import ArbitrageStateMachine, State
from atlas.outbox.queue import OutboxEntry, OutboxEntryType, OutboxQueue

_PAIR = TradingPair(ticker=Ticker.BTC, quote=Quote.USDT)
_SIGNAL = ArbSignal(
    exchange=Exchange.BINANCE,
    leg1_pair=_PAIR,
    leg1_side=Side.BUY,
    leg1_quantity=Decimal("0.01"),
    leg2_pair=_PAIR,
    leg2_side=Side.BUY,
    leg2_quantity=Decimal("0.01"),
    leg3_pair=_PAIR,
    leg3_side=Side.SELL,
    leg3_quantity=Decimal("0.01"),
    expected_profit=Decimal("5"),
)


class _FakeExchange:
    def __init__(self, *, hang_on: set[int] | None = None, raise_on: set[int] | None = None):
        self.placed: list[Order] = []
        self._hang_on = hang_on or set()
        self._raise_on = raise_on or set()

    async def place_order(self, order: Order) -> OrderResult:
        call_idx = len(self.placed)
        self.placed.append(order)
        if call_idx in self._raise_on:
            raise RuntimeError("synthetic exchange failure")
        if call_idx in self._hang_on:
            await asyncio.sleep(100)
        return OrderResult(id=order.id, status=OrderStatus.FILLED, filled=order.quantity)


def _sm(exchange: _FakeExchange, outbox: OutboxQueue) -> ArbitrageStateMachine:
    return ArbitrageStateMachine(
        exchange=exchange,
        leg1_timeout=0.01,
        leg2_timeout=0.01,
        leg3_timeout=0.01,
        outbox=outbox,
    )


def _drain(queue: OutboxQueue) -> list[OutboxEntry]:
    entries: list[OutboxEntry] = []
    while not queue.empty():
        entries.append(queue.get_nowait())
    return entries


# ---------------------------------------------------------------------------
# COMPLETE path
# ---------------------------------------------------------------------------


async def test_outbox_receives_complete_on_happy_path():
    outbox: OutboxQueue = asyncio.Queue()
    sm = _sm(_FakeExchange(), outbox)

    await sm.start(_SIGNAL)

    entries = _drain(outbox)
    trade_results = [e for e in entries if e.entry_type == OutboxEntryType.TRADE_RESULT]
    assert any(e.payload["state"] == "COMPLETE" for e in trade_results), (
        "Expected COMPLETE entry in outbox after successful 3-leg arbitrage"
    )


async def test_outbox_complete_contains_arb_id():
    outbox: OutboxQueue = asyncio.Queue()
    sm = _sm(_FakeExchange(), outbox)

    await sm.start(_SIGNAL)

    entries = _drain(outbox)
    complete = next(
        e
        for e in entries
        if e.entry_type == OutboxEntryType.TRADE_RESULT and e.payload["state"] == "COMPLETE"
    )
    assert complete.payload.get("arb_id"), "COMPLETE entry must carry arb_id"


# ---------------------------------------------------------------------------
# UNWIND_COMPLETE paths (leg2 timeout, leg3 timeout, exception)
# ---------------------------------------------------------------------------


async def test_outbox_receives_unwind_complete_on_leg2_timeout():
    outbox: OutboxQueue = asyncio.Queue()
    sm = _sm(_FakeExchange(hang_on={1}), outbox)

    await sm.start(_SIGNAL)

    entries = _drain(outbox)
    states = [e.payload["state"] for e in entries if e.entry_type == OutboxEntryType.TRADE_RESULT]
    assert "UNWIND_COMPLETE" in states


async def test_outbox_receives_unwind_complete_on_leg3_timeout():
    outbox: OutboxQueue = asyncio.Queue()
    sm = _sm(_FakeExchange(hang_on={2}), outbox)

    await sm.start(_SIGNAL)

    entries = _drain(outbox)
    states = [e.payload["state"] for e in entries if e.entry_type == OutboxEntryType.TRADE_RESULT]
    assert "UNWIND_COMPLETE" in states


async def test_outbox_receives_unwind_complete_on_exception():
    outbox: OutboxQueue = asyncio.Queue()
    # leg1 OK, leg2 raises → triggers exception-path unwind
    sm = _sm(_FakeExchange(raise_on={1}), outbox)

    await sm.start(_SIGNAL)

    entries = _drain(outbox)
    states = [e.payload["state"] for e in entries if e.entry_type == OutboxEntryType.TRADE_RESULT]
    assert "UNWIND_COMPLETE" in states


# ---------------------------------------------------------------------------
# TIMEOUT path (leg1)
# ---------------------------------------------------------------------------


async def test_outbox_receives_timeout_on_leg1_timeout():
    outbox: OutboxQueue = asyncio.Queue()
    sm = _sm(_FakeExchange(hang_on={0}), outbox)

    await sm.start(_SIGNAL)

    entries = _drain(outbox)
    states = [e.payload["state"] for e in entries if e.entry_type == OutboxEntryType.TRADE_RESULT]
    assert "TIMEOUT" in states


# ---------------------------------------------------------------------------
# FAILED path (unwind also fails)
# ---------------------------------------------------------------------------


async def test_outbox_receives_failed_when_unwind_also_fails():
    outbox: OutboxQueue = asyncio.Queue()
    # leg1 OK, leg2 raises, leg2-unwind raises (call #2) → FAILED
    sm = _sm(_FakeExchange(raise_on={1, 2}), outbox)

    await sm.start(_SIGNAL)

    entries = _drain(outbox)
    states = [e.payload["state"] for e in entries if e.entry_type == OutboxEntryType.TRADE_RESULT]
    assert "FAILED" in states


# ---------------------------------------------------------------------------
# No outbox — must not raise
# ---------------------------------------------------------------------------


async def test_no_outbox_does_not_raise():
    sm = ArbitrageStateMachine(
        exchange=_FakeExchange(),
        leg1_timeout=0.01,
        leg2_timeout=0.01,
        leg3_timeout=0.01,
        outbox=None,
    )
    await sm.start(_SIGNAL)  # should complete without error
    assert sm.state == State.IDLE


# ---------------------------------------------------------------------------
# AlertWorker integration: entries produced by state machine are consumable
# ---------------------------------------------------------------------------


async def test_alert_worker_consumes_state_machine_outbox():
    """End-to-end: state machine enqueues → AlertWorker receives the entry."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from atlas.outbox.workers import AlertWorker

    outbox: OutboxQueue = asyncio.Queue()
    sm = _sm(_FakeExchange(), outbox)
    worker = AlertWorker(queue=outbox, webhook_url="https://discord.fake/hook")

    await sm.start(_SIGNAL)

    mock_resp = MagicMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_sess = MagicMock()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=False)
    mock_sess.post = MagicMock(return_value=mock_resp)

    with patch("aiohttp.ClientSession", return_value=mock_sess):
        task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # COMPLETE entry must have reached AlertWorker and triggered a Discord POST.
    assert mock_sess.post.called, "AlertWorker should have posted to Discord after COMPLETE"
