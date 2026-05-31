from decimal import Decimal
from dataclasses import dataclass

# 금액은 반드시 Decimal — float 사용 금지 (부동소수점 오차)
Amount = Decimal
Symbol = str    # "BTC/USDT"
Exchange = str  # "binance"


@dataclass(frozen=True)
class TradingPair:
    base: str   # "BTC"
    quote: str  # "USDT"

    @classmethod
    def from_symbol(cls, symbol: Symbol) -> "TradingPair":
        base, quote = symbol.split("/")
        return cls(base=base, quote=quote)

    def __str__(self) -> Symbol:
        return f"{self.base}/{self.quote}"
