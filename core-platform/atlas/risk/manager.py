from decimal import Decimal

from atlas.execution.arb_signal import ArbSignal


class RiskDecision:
    APPROVED = "approved"
    REJECTED = "rejected"


class RiskManager:
    def __init__(self, max_order_size: Decimal, max_exposure: Decimal) -> None:
        self._max_order_size = max_order_size
        self._max_exposure = max_exposure
        self._kill_switch = False
        self._connected = True

    def check(self, signal: ArbSignal) -> str:
        if self._kill_switch:
            return RiskDecision.REJECTED
        if not self._connected:
            return RiskDecision.REJECTED
        quantities = [signal.leg1_quantity, signal.leg2_quantity, signal.leg3_quantity]
        if any(q > self._max_order_size for q in quantities):
            return RiskDecision.REJECTED
        if sum(quantities) > self._max_exposure:
            return RiskDecision.REJECTED
        return RiskDecision.APPROVED

    def set_kill_switch(self, enabled: bool) -> None:
        self._kill_switch = enabled

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
