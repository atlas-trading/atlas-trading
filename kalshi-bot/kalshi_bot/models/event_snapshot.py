from dataclasses import dataclass

from kalshi_bot.models.market_quote import MarketQuote


@dataclass(frozen=True, kw_only=True)
class EventSnapshot:
    event_ticker: str
    title: str
    mutually_exclusive: bool
    markets: tuple[MarketQuote, ...]
