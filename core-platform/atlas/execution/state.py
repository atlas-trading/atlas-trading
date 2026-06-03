import asyncio
import uuid
from decimal import Decimal
from enum import Enum, auto

from atlas.exchange.exchange_interface import ExchangeInterface
from atlas.exchange.order_result import OrderResult
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.order import Order
from atlas.execution.order_type import OrderType
from atlas.execution.side import Side

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
    ) -> None:
        self._exchange = exchange
        self._leg1_timeout = leg1_timeout
        self._leg2_timeout = leg2_timeout
        self._leg3_timeout = leg3_timeout
        self.state = State.IDLE

    async def start(self, signal: ArbSignal) -> None:
        if self.state != State.IDLE:
            return

        self.state = State.LEG1_PENDING
        leg1 = await self._place(
            signal, signal.leg1_pair, signal.leg1_side, signal.leg1_quantity, self._leg1_timeout
        )
        if leg1 is None:
            self.state = State.IDLE
            return

        self.state = State.LEG1_FILLED
        self.state = State.LEG2_PENDING
        leg2 = await self._place(
            signal, signal.leg2_pair, signal.leg2_side, signal.leg2_quantity, self._leg2_timeout
        )
        if leg2 is None:
            self.state = State.UNWINDING
            await self._unwind(signal, signal.leg1_pair, signal.leg1_side, leg1)
            self.state = State.UNWIND_COMPLETE
            self.state = State.IDLE
            return

        self.state = State.LEG2_FILLED
        self.state = State.LEG3_PENDING
        leg3 = await self._place(
            signal, signal.leg3_pair, signal.leg3_side, signal.leg3_quantity, self._leg3_timeout
        )
        if leg3 is None:
            self.state = State.UNWINDING
            await self._unwind(signal, signal.leg2_pair, signal.leg2_side, leg2)
            await self._unwind(signal, signal.leg1_pair, signal.leg1_side, leg1)
            self.state = State.UNWIND_COMPLETE
            self.state = State.IDLE
            return

        self.state = State.COMPLETE
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
