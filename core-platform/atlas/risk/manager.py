from decimal import Decimal
from enum import StrEnum

from atlas.core.quote import Quote
from atlas.core.trading_pair import TradingPair
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.side import Side


class RiskDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


_USDT = Quote.USDT


class RiskManager:
    """
    Pre-trade risk gate.

    `max_order_size` and `max_exposure` are both expressed in **USDT notional**.
    Each leg's notional is computed by converting its base-asset quantity into
    USDT via the most recent price seen on the matching ticker-vs-USDT pair.
    If no such price is cached, the signal is rejected — better safe than sorry.
    """

    def __init__(self, max_order_size: Decimal, max_exposure: Decimal) -> None:
        self._max_order_size = max_order_size
        self._max_exposure = max_exposure
        self._kill_switch = False
        self._connected = True
        # Mapping of TradingPair (base/USDT) → last seen mid/last price.
        self._usdt_prices: dict[TradingPair, Decimal] = {}

    def check(self, signal: ArbSignal) -> RiskDecision:
        if self._kill_switch:
            return RiskDecision.REJECTED
        if not self._connected:
            return RiskDecision.REJECTED

        legs = (
            (signal.leg1_pair, signal.leg1_side, signal.leg1_quantity),
            (signal.leg2_pair, signal.leg2_side, signal.leg2_quantity),
            (signal.leg3_pair, signal.leg3_side, signal.leg3_quantity),
        )
        notionals: list[Decimal] = []
        for pair, _side, qty in legs:
            usdt_value = self._leg_usdt_notional(pair, qty)
            if usdt_value is None:
                # Cannot value this leg → reject conservatively.
                return RiskDecision.REJECTED
            notionals.append(usdt_value)

        if any(n > self._max_order_size for n in notionals):
            return RiskDecision.REJECTED
        if sum(notionals) > self._max_exposure:
            return RiskDecision.REJECTED

        return RiskDecision.APPROVED

    def set_kill_switch(self, enabled: bool) -> None:
        self._kill_switch = enabled

    def set_connected(self, connected: bool) -> None:
        self._connected = connected

    def update_prices(self, prices: dict[TradingPair, Decimal]) -> None:
        """Push the latest USDT mid prices in for use by `check`."""
        for pair, price in prices.items():
            if pair.quote == _USDT and price > 0:
                self._usdt_prices[pair] = price

    def _leg_usdt_notional(self, pair: TradingPair, quantity: Decimal) -> Decimal | None:
        # The quantity is in base asset units. We need the value of those base
        # units in USDT. If the pair already quotes against USDT, multiply by
        # the cached price. Otherwise, look up the base asset's USDT pair.
        if pair.quote == _USDT:
            price = self._usdt_prices.get(pair)
            return None if price is None else quantity * price
        # Non-USDT-quoted leg (e.g. ETH/BTC): we still need to value the base
        # in USDT, which means looking up base/USDT.
        base_usdt = TradingPair(ticker=pair.ticker, quote=_USDT)
        price = self._usdt_prices.get(base_usdt)
        return None if price is None else quantity * price


# Re-export for callers that previously imported Side from this module's tests.
__all__ = ["RiskDecision", "RiskManager", "Side"]
