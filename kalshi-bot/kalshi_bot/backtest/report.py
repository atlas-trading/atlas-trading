import statistics
from collections import Counter, defaultdict
from decimal import Decimal

from kalshi_bot.backtest.replay import EventReplayResult


def build_summary(results: list[EventReplayResult]) -> dict:
    hit_counts: Counter[str] = Counter()
    event_counts: dict[str, set[str]] = defaultdict(set)
    net_per_contract: dict[str, list[Decimal]] = defaultdict(list)
    for result in results:
        for hit in result.hits:
            kind = hit.opportunity.kind.value
            hit_counts[kind] += 1
            event_counts[kind].add(result.event_ticker)
            net_per_contract[kind].append(hit.opportunity.net_edge_per_contract)
    kinds = {}
    for kind, count in hit_counts.items():
        nets = sorted(net_per_contract[kind])
        kinds[kind] = {
            "bar_hits": count,
            "distinct_events": len(event_counts[kind]),
            "net_per_contract_min": str(nets[0]),
            "net_per_contract_median": str(statistics.median(nets)),
            "net_per_contract_max": str(nets[-1]),
        }
    return {
        "events_replayed": len(results),
        "bars_replayed": sum(r.bars_replayed for r in results),
        "kinds": kinds,
    }


def format_summary(summary: dict) -> str:
    lines = [
        f"events replayed : {summary['events_replayed']}",
        f"bars replayed   : {summary['bars_replayed']}",
    ]
    if not summary["kinds"]:
        lines.append("no opportunities detected")
        return "\n".join(lines)
    for kind, stats in summary["kinds"].items():
        lines.append(
            f"{kind}: {stats['bar_hits']} bar-hits across {stats['distinct_events']} events, "
            f"net/contract min={stats['net_per_contract_min']} "
            f"median={stats['net_per_contract_median']} max={stats['net_per_contract_max']}"
        )
    return "\n".join(lines)
