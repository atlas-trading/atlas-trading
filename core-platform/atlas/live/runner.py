from decimal import Decimal
from typing import Any

from atlas.core.parsers import parse_trading_pair
from atlas.core.quote import Quote
from atlas.core.trading_pair import TradingPair
from atlas.exchange.exchange_interface import ExchangeInterface
from atlas.execution.engine import ExecutionEngine
from atlas.market.feed import MarketDataFeed
from atlas.strategy.strategy import Strategy


class LiveRunner:
    def __init__(
        self,
        exchange: ExchangeInterface,
        feed: MarketDataFeed,
        strategy: Strategy,
        engine: ExecutionEngine,
        verbose: bool = False,
    ) -> None:
        self._exchange = exchange
        self._feed = feed
        self._strategy = strategy
        self._engine = engine
        self._verbose = verbose

    async def on_tickers(self, tickers: dict[str, Any]) -> None:
        if self._verbose:
            preview = " | ".join(
                f"{s} {d.get('bid') or d.get('last')}/{d.get('ask') or d.get('last')}"
                for s, d in list(tickers.items())[:4]
            )
            suffix = f" +{len(tickers) - 4} more" if len(tickers) > 4 else ""
            print(f"[TICK] {preview}{suffix}")

        self._engine.update_prices(_extract_usdt_prices(tickers))
        await self._feed.on_tickers(tickers)
        signals = self._strategy.on_tickers(tickers)

        if self._verbose and signals:
            for sig in signals:
                pct = float(sig.expected_profit / sig.leg1_quantity) * 100
                print(
                    f"[SIGNAL] {sig.leg1_side.upper()} {sig.leg1_pair}"
                    f" → {sig.leg2_side.upper()} {sig.leg2_pair}"
                    f" → {sig.leg3_side.upper()} {sig.leg3_pair}"
                    f" | profit≈{pct:.3f}% qty={sig.leg1_quantity}"
                )

        for signal in signals:
            await self._engine.on_signal(signal)

    async def run(self) -> None:
        await self._exchange.subscribe_ticker(
            trading_pairs=self._strategy.all_pairs(),
            callback=self.on_tickers,
        )


def _extract_usdt_prices(tickers: dict[str, Any]) -> dict[TradingPair, Decimal]:
    """Pick out only the USDT-quoted pairs so the risk manager can value legs."""
    out: dict[TradingPair, Decimal] = {}
    for symbol, data in tickers.items():
        try:
            pair = parse_trading_pair(symbol)
        except (ValueError, KeyError):
            continue
        if pair.quote != Quote.USDT:
            continue
        last = data.get("last") or 0
        bid = data.get("bid") or last
        ask = data.get("ask") or last
        if bid and ask:
            mid = (Decimal(str(bid)) + Decimal(str(ask))) / Decimal("2")
            out[pair] = mid
    return out
