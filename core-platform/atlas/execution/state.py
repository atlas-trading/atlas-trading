import asyncio
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
            print(msg)

    async def start(self, signal: ArbSignal) -> None:
        if self.state != State.IDLE:
            return

        arb_id = str(uuid.uuid4())
        await self._db_create_arb(arb_id, signal)

        self.state = State.LEG1_PENDING
        self._log(
            f"[LEG1] {signal.leg1_side.upper()} {signal.leg1_pair} qty={signal.leg1_quantity}"
        )
        leg1 = await self._place(
            signal, signal.leg1_pair, signal.leg1_side, signal.leg1_quantity, self._leg1_timeout
        )
        if leg1 is None:
            self._log("[LEG1] TIMEOUT → IDLE")
            await self._db_finish_arb(arb_id, "TIMEOUT")
            self.state = State.IDLE
            return
        self._log(f"[LEG1] FILLED avg={leg1.average}")
        await self._db_save_order(
            arb_id, leg1, signal, signal.leg1_pair, signal.leg1_side, signal.leg1_quantity
        )

        self.state = State.LEG1_FILLED
        self.state = State.LEG2_PENDING
        self._log(
            f"[LEG2] {signal.leg2_side.upper()} {signal.leg2_pair} qty={signal.leg2_quantity}"
        )
        leg2 = await self._place(
            signal, signal.leg2_pair, signal.leg2_side, signal.leg2_quantity, self._leg2_timeout
        )
        if leg2 is None:
            self._log("[LEG2] TIMEOUT → UNWIND")
            self.state = State.UNWINDING
            await self._unwind(signal, signal.leg1_pair, signal.leg1_side, leg1)
            await self._db_finish_arb(arb_id, "UNWIND_COMPLETE")
            self.state = State.UNWIND_COMPLETE
            self.state = State.IDLE
            return
        self._log(f"[LEG2] FILLED avg={leg2.average}")
        await self._db_save_order(
            arb_id, leg2, signal, signal.leg2_pair, signal.leg2_side, signal.leg2_quantity
        )

        self.state = State.LEG2_FILLED
        self.state = State.LEG3_PENDING
        self._log(
            f"[LEG3] {signal.leg3_side.upper()} {signal.leg3_pair} qty={signal.leg3_quantity}"
        )
        leg3 = await self._place(
            signal, signal.leg3_pair, signal.leg3_side, signal.leg3_quantity, self._leg3_timeout
        )
        if leg3 is None:
            self._log("[LEG3] TIMEOUT → UNWIND")
            self.state = State.UNWINDING
            await self._unwind(signal, signal.leg2_pair, signal.leg2_side, leg2)
            await self._unwind(signal, signal.leg1_pair, signal.leg1_side, leg1)
            await self._db_finish_arb(arb_id, "UNWIND_COMPLETE")
            self.state = State.UNWIND_COMPLETE
            self.state = State.IDLE
            return
        self._log(f"[LEG3] FILLED avg={leg3.average}")
        await self._db_save_order(
            arb_id, leg3, signal, signal.leg3_pair, signal.leg3_side, signal.leg3_quantity
        )

        self.state = State.COMPLETE
        self._log(
            f"[COMPLETE] expected_profit={signal.expected_profit:.6f}"
            f" ({float(signal.expected_profit / signal.leg1_quantity) * 100:.3f}%)"
        )
        await self._db_finish_arb(arb_id, "COMPLETE", actual_profit=signal.expected_profit)
        self.state = State.IDLE

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
        filled = Decimal(str(result.filled)) if result.filled else Decimal("0")
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

    async def _db_finish_arb(
        self, arb_id: str, status: str, actual_profit: Decimal | None = None
    ) -> None:
        if self._session_factory is None:
            return
        from atlas.db.models import ArbAttempt

        async with self._session_factory() as session:
            attempt = await session.get(ArbAttempt, arb_id)
            if attempt:
                attempt.status = status
                attempt.actual_profit = actual_profit
                attempt.completed_at = datetime.now(timezone.utc)
                await session.commit()
