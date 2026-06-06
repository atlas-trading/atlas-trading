import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from atlas.core.parsers import parse_trading_pair, to_ccxt_symbol
from atlas.core.quote import Quote
from atlas.core.trading_pair import TradingPair
from atlas.execution.arb_signal import ArbSignal
from atlas.execution.engine import ExecutionEngine
from atlas.execution.state import ArbitrageStateMachine
from atlas.outbox.queue import OutboxEntryType, OutboxQueue
from atlas.risk.manager import RiskManager
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy

from .exchange import BacktestExchange


@dataclass(frozen=True, kw_only=True)
class TradeRecord:
    timestamp: datetime
    arb_id: str
    leg1_pair: str
    leg2_pair: str
    leg3_pair: str
    expected_profit: Decimal
    actual_profit: Decimal | None
    status: str


class BacktestRunner:
    def __init__(
        self,
        feed: Any,
        exchange: BacktestExchange,
        strategy: TriangularArbitrageStrategy,
        risk_manager: RiskManager,
    ) -> None:
        self._feed = feed
        self._exchange = exchange
        self._strategy = strategy
        self._outbox: OutboxQueue = asyncio.Queue()
        state_machine = ArbitrageStateMachine(exchange=exchange, outbox=self._outbox)
        self._engine = ExecutionEngine(risk_manager=risk_manager, state_machine=state_machine)
        self._records: list[TradeRecord] = []

    async def run(self, start: datetime, end: datetime) -> list[TradeRecord]:
        async for ts, tickers in self._feed.stream(start, end):
            self._exchange.update_prices(tickers)
            self._engine.update_prices(_extract_usdt_prices(tickers))
            signals = self._strategy.on_tickers(tickers)
            for signal in signals:
                await self._engine.on_signal(signal)
                self._drain_outbox(ts, signal)
        return self._records

    def _drain_outbox(self, ts: datetime, signal: ArbSignal) -> None:
        while not self._outbox.empty():
            entry = self._outbox.get_nowait()
            if entry.entry_type != OutboxEntryType.TRADE_RESULT:
                continue
            p = entry.payload
            net_pnl = Decimal(p["net_pnl"]) if p.get("net_pnl") else None
            self._records.append(
                TradeRecord(
                    timestamp=ts,
                    arb_id=p["arb_id"],
                    leg1_pair=to_ccxt_symbol(signal.leg1_pair),
                    leg2_pair=to_ccxt_symbol(signal.leg2_pair),
                    leg3_pair=to_ccxt_symbol(signal.leg3_pair),
                    expected_profit=signal.expected_profit,
                    actual_profit=net_pnl,
                    status=p["state"],
                )
            )


def _extract_usdt_prices(tickers: dict[str, Any]) -> dict[TradingPair, Decimal]:
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
