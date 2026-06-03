from typing import Any, Protocol

from atlas.core.trading_pair import TradingPair
from atlas.execution.arb_signal import ArbSignal


class Strategy(Protocol):
    def all_pairs(self) -> list[TradingPair]: ...

    def on_tickers(self, tickers: dict[str, Any]) -> list[ArbSignal]: ...
