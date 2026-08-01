from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class MarketQuote:
    ticker: str
    status: str
    yes_bid: Decimal
    yes_ask: Decimal
    yes_bid_size: Decimal
    yes_ask_size: Decimal

    @property
    def no_ask(self) -> Decimal:
        return Decimal(1) - self.yes_bid

    @property
    def no_ask_size(self) -> Decimal:
        return self.yes_bid_size

    @property
    def no_bid(self) -> Decimal:
        return Decimal(1) - self.yes_ask
