from typing import Any

from atlas.exchange.exchange_interface import ExchangeInterface
from atlas.execution.engine import ExecutionEngine
from atlas.market.feed import MarketDataFeed
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy


class LiveRunner:
    def __init__(
        self,
        adapter: ExchangeInterface,
        feed: MarketDataFeed,
        strategy: TriangularArbitrageStrategy,
        engine: ExecutionEngine,
    ) -> None:
        self._adapter = adapter
        self._feed = feed
        self._strategy = strategy
        self._engine = engine

    async def on_tickers(self, tickers: dict[str, Any]) -> None:
        await self._feed.on_tickers(tickers)
        signals = self._strategy.on_tickers(tickers)
        for signal in signals:
            await self._engine.on_signal(signal)

    async def run(self) -> None:
        await self._adapter.subscribe_ticker(
            trading_pairs=self._strategy.all_pairs(),
            callback=self.on_tickers,
        )
