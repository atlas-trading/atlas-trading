from typing import Protocol

from atlas.execution.arb_signal import ArbSignal
from atlas.risk.manager import RiskDecision, RiskManager


class StateMachine(Protocol):
    async def start(self, signal: ArbSignal) -> None: ...


class ExecutionEngine:
    def __init__(self, risk_manager: RiskManager, state_machine: StateMachine) -> None:
        self._risk = risk_manager
        self._state_machine = state_machine

    async def on_signal(self, signal: ArbSignal) -> None:
        if self._risk.check(signal) == RiskDecision.REJECTED:
            return

        await self._state_machine.start(signal)
