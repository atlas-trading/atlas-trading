import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING

from atlas.exchange.exchange_interface import ExchangeInterface
from atlas.exchange.order_result import OrderResult
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.order import Order
from atlas.execution.order_type import OrderType
from atlas.execution.side import Side

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

_log = logging.getLogger(__name__)

_LEG1_TIMEOUT = 0.5
_LEG2_TIMEOUT = 0.3
_LEG3_TIMEOUT = 0.3


class State(Enum):
    IDLE = auto()
    LEG1_PENDING = auto()
    LEG1_FILLED = auto()
    LEG2_PENDING = auto()
    LEG2_FILLED = auto()
    LEG3_PENDING = auto()
    COMPLETE = auto()
    UNWINDING = auto()
    UNWIND_COMPLETE = auto()


class ArbitrageStateMachine:
    def __init__(
        self,
        exchange: ExchangeInterface,
        leg1_timeout: float = _LEG1_TIMEOUT,
        leg2_timeout: float = _LEG2_TIMEOUT,
        leg3_timeout: float = _LEG3_TIMEOUT,
        verbose: bool = False,
        session_factory: "async_sessionmaker | None" = None,
    ) -> None:
        self._exchange = exchange
        self._leg1_timeout = leg1_timeout
        self._leg2_timeout = leg2_timeout
        self._leg3_timeout = leg3_timeout
        self._verbose = verbose
        self._session_factory = session_factory
        self.state = State.IDLE

    def _log(self, msg: str) -> None:
        if self._verbose:
            _log.info(msg)

    async def start(self, signal: ArbSignal) -> None:
        if self.state != State.IDLE:
            return

        arb_id = str(uuid.uuid4())
        await self._db_create_arb(arb_id, signal)

        leg1: OrderResult | None = None
        leg2: OrderResult | None = None

        try:
            # ---------------- LEG 1 ----------------
            self.state = State.LEG1_PENDING
            self._log(
                f"[LEG1] {signal.leg1_side.upper()} {signal.leg1_pair} qty={signal.leg1_quantity}"
            )
            leg1 = await self._place(
                signal,
                signal.leg1_pair,
                signal.leg1_side,
                signal.leg1_quantity,
                self._leg1_timeout,
            )
            if leg1 is None:
                self._log("[LEG1] TIMEOUT → IDLE")
                await self._db_update_arb_status(arb_id, "TIMEOUT")
                return
            self._log(f"[LEG1] FILLED avg={leg1.average}")
            await self._db_save_order(
                arb_id, leg1, signal, signal.leg1_pair, signal.leg1_side, signal.leg1_quantity
            )
            self.state = State.LEG1_FILLED
            await self._db_update_arb_status(arb_id, "LEG1_FILLED")

            # Propagate actual fill: scale subsequent legs by how much leg1 actually filled.
            fill1 = leg1.filled if leg1.filled is not None else signal.leg1_quantity
            ratio1 = fill1 / signal.leg1_quantity if signal.leg1_quantity else Decimal("1")
            leg2_qty = signal.leg2_quantity * ratio1

            # ---------------- LEG 2 ----------------
            self.state = State.LEG2_PENDING
            self._log(f"[LEG2] {signal.leg2_side.upper()} {signal.leg2_pair} qty={leg2_qty}")
            leg2 = await self._place(
                signal,
                signal.leg2_pair,
                signal.leg2_side,
                leg2_qty,
                self._leg2_timeout,
            )
            if leg2 is None:
                self._log("[LEG2] TIMEOUT → UNWIND")
                self.state = State.UNWINDING
                await self._unwind(signal, signal.leg1_pair, signal.leg1_side, leg1)
                await self._db_update_arb_status(arb_id, "UNWIND_COMPLETE")
                self.state = State.UNWIND_COMPLETE
                return
            self._log(f"[LEG2] FILLED avg={leg2.average}")
            await self._db_save_order(
                arb_id, leg2, signal, signal.leg2_pair, signal.leg2_side, leg2_qty
            )
            self.state = State.LEG2_FILLED
            await self._db_update_arb_status(arb_id, "LEG2_FILLED")

            # Scale leg3 by how much leg2 actually filled relative to what was ordered.
            fill2 = leg2.filled if leg2.filled is not None else leg2_qty
            ratio2 = fill2 / leg2_qty if leg2_qty else Decimal("1")
            leg3_qty = signal.leg3_quantity * ratio1 * ratio2

            # ---------------- LEG 3 ----------------
            self.state = State.LEG3_PENDING
            self._log(f"[LEG3] {signal.leg3_side.upper()} {signal.leg3_pair} qty={leg3_qty}")
            leg3 = await self._place(
                signal,
                signal.leg3_pair,
                signal.leg3_side,
                leg3_qty,
                self._leg3_timeout,
            )
            if leg3 is None:
                self._log("[LEG3] TIMEOUT → UNWIND")
                self.state = State.UNWINDING
                await self._unwind(signal, signal.leg2_pair, signal.leg2_side, leg2)
                await self._unwind(signal, signal.leg1_pair, signal.leg1_side, leg1)
                await self._db_update_arb_status(arb_id, "UNWIND_COMPLETE")
                self.state = State.UNWIND_COMPLETE
                return
            self._log(f"[LEG3] FILLED avg={leg3.average}")
            await self._db_save_order(
                arb_id, leg3, signal, signal.leg3_pair, signal.leg3_side, leg3_qty
            )

            self.state = State.COMPLETE
            self._log(
                f"[COMPLETE] expected_profit={signal.expected_profit:.6f}"
                f" ({float(signal.expected_profit / signal.leg1_quantity) * 100:.3f}%)"
            )
            await self._db_update_arb_status(
                arb_id,
                "COMPLETE",
                actual_profit=self._actual_profit(signal, leg1, leg2, leg3),
            )
        except asyncio.CancelledError:
            # Honour cooperative cancellation: do NOT attempt to unwind here,
            # because the runtime is tearing the loop down.
            raise
        except Exception:
            _log.exception("[STATE] unexpected error during arbitrage; attempting unwind")
            self.state = State.UNWINDING
            try:
                if leg2 is not None:
                    await self._unwind(signal, signal.leg2_pair, signal.leg2_side, leg2)
                if leg1 is not None:
                    await self._unwind(signal, signal.leg1_pair, signal.leg1_side, leg1)
                await self._db_update_arb_status(arb_id, "UNWIND_COMPLETE")
            except Exception:
                _log.exception("[STATE] unwind also failed")
                await self._db_update_arb_status(arb_id, "FAILED")
        finally:
            self.state = State.IDLE

    def _actual_profit(
        self,
        signal: ArbSignal,
        r1: OrderResult,
        r2: OrderResult,
        r3: OrderResult,
    ) -> Decimal:
        def _input_qty(result: OrderResult, planned: Decimal, side: Side) -> Decimal:
            filled = Decimal(str(result.filled)) if result.filled is not None else planned
            if side == Side.SELL:
                return filled
            cost = Decimal(str(result.cost)) if result.cost is not None else None
            avg = Decimal(str(result.average)) if result.average is not None else Decimal("0")
            return cost if cost is not None else filled * avg

        def _output_qty(result: OrderResult, planned: Decimal, side: Side) -> Decimal:
            filled = Decimal(str(result.filled)) if result.filled is not None else planned
            if side == Side.BUY:
                return filled
            cost = Decimal(str(result.cost)) if result.cost is not None else None
            avg = Decimal(str(result.average)) if result.average is not None else Decimal("0")
            return cost if cost is not None else filled * avg

        start = _input_qty(r1, signal.leg1_quantity, signal.leg1_side)
        end = _output_qty(r3, signal.leg3_quantity, signal.leg3_side)
        return end - start if start > 0 else signal.expected_profit

    async def _place(
        self,
        signal: ArbSignal,
        pair,
        side: Side,
        quantity: Decimal,
        timeout: float,
    ) -> OrderResult | None:
        order = Order(
            id=str(uuid.uuid4()),
            exchange=signal.exchange,
            trading_pair=pair,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
        )
        try:
            return await asyncio.wait_for(self._exchange.place_order(order), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def _unwind(self, signal: ArbSignal, pair, side: Side, result: OrderResult) -> None:
        filled = result.filled if result.filled else Decimal("0")
        if filled == 0:
            return
        reverse = Side.SELL if side == Side.BUY else Side.BUY
        order = Order(
            id=str(uuid.uuid4()),
            exchange=signal.exchange,
            trading_pair=pair,
            side=reverse,
            order_type=OrderType.MARKET,
            quantity=filled,
        )
        await self._exchange.place_order(order)

    async def _db_create_arb(self, arb_id: str, signal: ArbSignal) -> None:
        if self._session_factory is None:
            return
        from atlas.db.models import ArbAttempt

        async with self._session_factory() as session:
            session.add(
                ArbAttempt(
                    id=arb_id,
                    strategy="triangular_arb",
                    status="PENDING",
                    expected_profit=signal.expected_profit,
                    created_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def _db_save_order(
        self,
        arb_id: str,
        result: OrderResult,
        signal: ArbSignal,
        pair,
        side: Side,
        quantity: Decimal,
    ) -> None:
        if self._session_factory is None or not result.id:
            return
        from atlas.db.models import OrderRecord

        async with self._session_factory() as session:
            session.add(
                OrderRecord(
                    id=result.id,
                    exchange=str(signal.exchange.value),
                    symbol=f"{pair.ticker}/{pair.quote}",
                    side=str(side.value),
                    order_type="market",
                    quantity=quantity,
                    status="filled",
                    arb_id=arb_id,
                    created_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def _db_update_arb_status(
        self, arb_id: str, status: str, actual_profit: Decimal | None = None
    ) -> None:
        if self._session_factory is None:
            return
        from atlas.db.models import ArbAttempt

        async with self._session_factory() as session:
            attempt = await session.get(ArbAttempt, arb_id)
            if attempt:
                attempt.status = status
                if actual_profit is not None:
                    attempt.actual_profit = actual_profit
                if status in {"COMPLETE", "UNWIND_COMPLETE", "TIMEOUT", "FAILED"}:
                    attempt.completed_at = datetime.now(timezone.utc)
                await session.commit()
