import asyncio
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.parsers import parse_trading_pair
from atlas.events.bus import EventBus
from atlas.events.market_data_event import MarketDataEvent
from atlas.market.tick import Tick


class MarketDataFeed:
    def __init__(self, exchange: Exchange, bus: EventBus, outbox: asyncio.Queue) -> None:
        self._exchange = exchange
        self._bus = bus
        self._outbox = outbox

    async def on_tickers(self, tickers: dict) -> None:
        for symbol, raw in tickers.items():
            tick = self._to_tick(symbol, raw)

            await self._bus.publish(
                MarketDataEvent(
                    exchange=self._exchange,
                    trading_pair=tick.trading_pair,
                    bid=tick.bid,
                    ask=tick.ask,
                    last=tick.last,
                )
            )
            self._outbox.put_nowait(tick)

    def _to_tick(self, symbol: str, raw: dict) -> Tick:
        return Tick(
            exchange=self._exchange,
            trading_pair=parse_trading_pair(symbol),
            timestamp=raw.get("timestamp") or 0,
            bid=Decimal(str(raw.get("bid") or 0)),
            ask=Decimal(str(raw.get("ask") or 0)),
            last=Decimal(str(raw.get("last") or 0)),
            volume=Decimal(str(raw.get("baseVolume") or 0)),
        )
