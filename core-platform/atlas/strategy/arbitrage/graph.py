import math
from dataclasses import dataclass
from decimal import Decimal

from atlas.core.trading_pair import TradingPair
from atlas.execution.side import Side

_EPS = 1e-10

# (from_currency, to_currency, log_weight, trading_pair, side)
_Edge = tuple[str, str, float, TradingPair, Side]
# pred chain entry: (predecessor_node, pair, side, log_weight)
_PredEntry = tuple[str, TradingPair, Side, float]


@dataclass(frozen=True, kw_only=True)
class ArbOpportunity:
    legs: tuple[tuple[TradingPair, Side], ...]
    rate: Decimal  # product of rates across all legs; > 1 means profit


def detect_arbitrage(prices: dict[TradingPair, tuple[Decimal, Decimal]]) -> ArbOpportunity | None:
    """
    Bellman-Ford negative cycle detection on the currency exchange graph.

    Edge weight = -log(rate), so a negative-weight cycle = product of rates > 1 = arbitrage.

    Uses a virtual source node connected to every real node with weight=0, so all nodes
    are reachable and dist[v] < inf after the first relaxation pass. After (n-1) full
    passes, a node whose dist would still decrease on the n-th pass lies on (or is
    reachable from) a negative cycle.
    """
    if not prices:
        return None

    edges = _build_edges(prices)
    if not edges:
        return None

    nodes = sorted({u for u, *_ in edges} | {v for _, v, *_ in edges})
    n = len(nodes)

    # virtual source: dist=0 here, +inf everywhere else, gets relaxed to 0 in pass 1
    dist: dict[str, float] = {node: 0.0 for node in nodes}
    pred: dict[str, _PredEntry | None] = {node: None for node in nodes}

    # n - 1 relaxation passes
    for _ in range(n - 1):
        updated = False
        for u, v, w, pair, side in edges:
            if dist[u] + w < dist[v] - _EPS:
                dist[v] = dist[u] + w
                pred[v] = (u, pair, side, w)
                updated = True
        if not updated:
            break

    # n-th pass: any further relaxation indicates a negative cycle reachable from v
    cycle_node: str | None = None
    for u, v, w, pair, side in edges:
        if dist[u] + w < dist[v] - _EPS:
            pred[v] = (u, pair, side, w)
            cycle_node = v
            break

    if cycle_node is None:
        return None

    # Walk back n times to guarantee we land on a node inside the cycle.
    node = cycle_node
    for _ in range(n):
        entry = pred[node]
        if entry is None:
            return None
        node = entry[0]

    # Now walk the cycle and collect legs from the pred chain (no edge re-scan needed).
    start = node
    legs: list[tuple[TradingPair, Side]] = []
    total_log_rate = 0.0

    current = start
    while True:
        entry = pred[current]
        if entry is None:
            return None
        prev_node, pair, side, w = entry
        legs.append((pair, side))
        total_log_rate -= w  # rate = exp(-w); product is sum of -w
        current = prev_node
        if current == start:
            break

    legs.reverse()
    rate = Decimal(str(math.exp(total_log_rate)))
    return ArbOpportunity(legs=tuple(legs), rate=rate)


def _build_edges(prices: dict[TradingPair, tuple[Decimal, Decimal]]) -> list[_Edge]:
    edges: list[_Edge] = []
    for pair, (bid, ask) in prices.items():
        if bid <= 0 or ask <= 0 or bid > ask:
            continue  # reject crossed book and invalid prices
        base = str(pair.ticker)
        quote = str(pair.quote)
        # BUY base with quote: 1 quote → 1/ask base. log(1/ask) = -log(ask) → weight=+log(ask)
        edges.append((quote, base, math.log(float(ask)), pair, Side.BUY))
        # SELL base for quote: 1 base → bid quote. log(bid) → weight=-log(bid)
        edges.append((base, quote, -math.log(float(bid)), pair, Side.SELL))
    return edges
