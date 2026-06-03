from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class CcxtTicker:
    symbol: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    high: float | None = None
    low: float | None = None
    bid: float | None = None
    bid_volume: float | None = None
    ask: float | None = None
    ask_volume: float | None = None
    vwap: float | None = None
    open: float | None = None
    close: float | None = None
    last: float | None = None
    previous_close: float | None = None
    change: float | None = None
    percentage: float | None = None
    average: float | None = None
    base_volume: float | None = None
    quote_volume: float | None = None
