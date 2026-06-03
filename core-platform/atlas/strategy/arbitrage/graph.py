import math
from dataclasses import dataclass
from decimal import Decimal

from atlas.core.trading_pair import TradingPair
from atlas.execution.side import Side

_EPS = 1e-10

# (from_currency, to_currency, log_weight, trading_pair, side)
_Edge = tuple[str, str, float, TradingPair, Side]
_PredEntry = tuple[str, TradingPair, Side]


@dataclass(frozen=True, kw_only=True)
class ArbOpportunity:
    legs: tuple[tuple[TradingPair, Side], ...]
    rate: Decimal  # product of rates across all legs; > 1 means profit


def detect_arbitrage(prices: dict[TradingPair, tuple[Decimal, Decimal]]) -> ArbOpportunity | None:
    """
    Bellman-Ford negative cycle detection on the currency exchange graph.

    Edge weight = -log(rate), so a negative-weight cycle = product of rates > 1 = arbitrage.
    """
    if not prices:
        return None

    edges = _build_edges(prices)
    nodes = sorted({u for u, *_ in edges} | {v for _, v, *_ in edges})
    n = len(nodes)

    dist: dict[str, float] = {node: 0.0 for node in nodes}
    pred: dict[str, _PredEntry | None] = {node: None for node in nodes}
    last_relaxed: str | None = None

    for _ in range(n):
        last_relaxed = None
        for u, v, w, pair, side in edges:
            if dist[u] + w < dist[v] - _EPS:
                dist[v] = dist[u] + w
                pred[v] = (u, pair, side)
                last_relaxed = v

    if last_relaxed is None:
        return None

    node = last_relaxed
    for _ in range(n):
        node = pred[node][0]  # type: ignore[index]

    start = node
    legs: list[tuple[TradingPair, Side]] = []
    total_log_rate = 0.0

    current = start
    while True:
        u, pair, side = pred[current]  # type: ignore[misc]
        for eu, ev, ew, ep, es in edges:
            if eu == u and ev == current and ep == pair and es == side:
                total_log_rate -= ew
                break
        legs.append((pair, side))
        current = u
        if current == start:
            break

    legs.reverse()
    rate = Decimal(str(math.exp(total_log_rate)))
    return ArbOpportunity(legs=tuple(legs), rate=rate)


def _build_edges(prices: dict[TradingPair, tuple[Decimal, Decimal]]) -> list[_Edge]:
    edges: list[_Edge] = []
    for pair, (bid, ask) in prices.items():
        base = str(pair.ticker)
        quote = str(pair.quote)
        if ask > 0:
            edges.append((quote, base, math.log(float(ask)), pair, Side.BUY))
        if bid > 0:
            edges.append((base, quote, -math.log(float(bid)), pair, Side.SELL))
    return edges
