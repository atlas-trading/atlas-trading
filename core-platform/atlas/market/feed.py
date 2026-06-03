import asyncio
from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.parsers import parse_trading_pair
from atlas.events.bus import EventBus
from atlas.events.market_data_event import MarketDataEvent
from atlas.exchange.ccxt_ticker import CcxtTicker
from atlas.market.tick import Tick


class MarketDataFeed:
    def __init__(self, exchange: Exchange, bus: EventBus, outbox: asyncio.Queue) -> None:
        self._exchange = exchange
        self._bus = bus
        self._outbox = outbox

    async def on_tickers(self, tickers: dict[str, CcxtTicker]) -> None:
        for symbol, ticker in tickers.items():
            tick = self._to_tick(symbol, ticker)

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

    def _to_tick(self, symbol: str, ticker: CcxtTicker) -> Tick:
        return Tick(
            exchange=self._exchange,
            trading_pair=parse_trading_pair(symbol),
            timestamp=ticker.timestamp or 0,
            bid=Decimal(str(ticker.bid or 0)),
            ask=Decimal(str(ticker.ask or 0)),
            last=Decimal(str(ticker.last or 0)),
            volume=Decimal(str(ticker.base_volume or 0)),
        )
