import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .runner import TradeRecord


@dataclass(frozen=True, kw_only=True)
class BacktestSummary:
    start: datetime
    end: datetime
    initial_balance: Decimal
    final_balance: Decimal
    records: list[TradeRecord]


def print_summary(summary: BacktestSummary) -> None:
    pnl = summary.final_balance - summary.initial_balance
    pnl_pct = (pnl / summary.initial_balance * 100) if summary.initial_balance else Decimal(0)

    completed = [r for r in summary.records if r.status == "COMPLETE"]
    unwind = sum(1 for r in summary.records if r.status == "UNWIND_COMPLETE")
    timeout = sum(1 for r in summary.records if r.status == "TIMEOUT")
    win_rate = len(completed) / len(summary.records) * 100 if summary.records else 0.0

    profits = [r.actual_profit for r in completed if r.actual_profit is not None]
    avg_pnl = sum(profits) / len(profits) if profits else Decimal(0)

    max_dd = _max_drawdown(summary.records)

    print(f"\n{'=' * 48}")
    print(f"Backtest: {summary.start.date()} → {summary.end.date()}")
    print(f"{'=' * 48}")
    print(f"초기 잔고:    {summary.initial_balance:.2f} USDT")
    print(f"최종 잔고:    {summary.final_balance:.2f} USDT")
    print(f"총 PnL:      {pnl:+.4f} USDT  ({pnl_pct:+.2f}%)")
    print(
        f"거래 수:      {len(summary.records)}"
        f"  (COMPLETE {len(completed)} / UNWIND {unwind} / TIMEOUT {timeout})"
    )
    print(f"승률:         {win_rate:.1f}%")
    print(f"평균 수익:   {avg_pnl:+.6f} USDT/거래")
    print(f"최대 낙폭:   -{max_dd:.4f} USDT")
    print(f"{'=' * 48}\n")


def _max_drawdown(records: list[TradeRecord]) -> Decimal:
    running = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    for r in records:
        if r.actual_profit is None:
            continue
        running += r.actual_profit
        if running > peak:
            peak = running
        dd = peak - running
        if dd > max_dd:
            max_dd = dd
    return max_dd


def to_csv(summary: BacktestSummary, path: str) -> None:
    fields = [
        "timestamp",
        "arb_id",
        "leg1_pair",
        "leg2_pair",
        "leg3_pair",
        "expected_profit",
        "actual_profit",
        "status",
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in summary.records:
            w.writerow(
                {
                    "timestamp": r.timestamp.isoformat(),
                    "arb_id": r.arb_id,
                    "leg1_pair": r.leg1_pair,
                    "leg2_pair": r.leg2_pair,
                    "leg3_pair": r.leg3_pair,
                    "expected_profit": str(r.expected_profit),
                    "actual_profit": str(r.actual_profit) if r.actual_profit is not None else "",
                    "status": r.status,
                }
            )
    print(f"결과 저장됨: {path}")
