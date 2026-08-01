import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from kalshi_bot.models import Opportunity, OrderResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    event_ticker TEXT NOT NULL,
    legs TEXT NOT NULL,
    count TEXT NOT NULL,
    gross_edge_total TEXT NOT NULL,
    fee_total TEXT NOT NULL,
    net_edge_total TEXT NOT NULL,
    executable INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    opportunity_id INTEGER,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    price TEXT NOT NULL,
    count TEXT NOT NULL,
    purpose TEXT NOT NULL,
    order_id TEXT,
    fill_count TEXT,
    remaining_count TEXT,
    average_fill_price TEXT,
    average_fee_paid TEXT,
    error TEXT
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def record_opportunity(self, opportunity: Opportunity) -> int:
        legs_json = json.dumps(
            [
                {
                    "ticker": leg.ticker,
                    "side": leg.side,
                    "price": str(leg.price),
                    "available_size": str(leg.available_size),
                }
                for leg in opportunity.legs
            ]
        )
        cursor = self._conn.execute(
            "INSERT INTO opportunities"
            " (ts, kind, event_ticker, legs, count, gross_edge_total, fee_total,"
            "  net_edge_total, executable)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _now(),
                opportunity.kind.value,
                opportunity.event_ticker,
                legs_json,
                str(opportunity.count),
                str(opportunity.gross_edge_total),
                str(opportunity.fee_total),
                str(opportunity.net_edge_total),
                int(opportunity.executable),
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid or 0)

    def record_order(
        self,
        *,
        opportunity_id: int | None,
        ticker: str,
        side: str,
        price: Decimal,
        count: Decimal,
        purpose: str,
        result: OrderResult | None = None,
        error: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO orders"
            " (ts, opportunity_id, ticker, side, price, count, purpose, order_id,"
            "  fill_count, remaining_count, average_fill_price, average_fee_paid, error)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _now(),
                opportunity_id,
                ticker,
                side,
                str(price),
                str(count),
                purpose,
                result.order_id if result else None,
                str(result.fill_count) if result else None,
                str(result.remaining_count) if result else None,
                str(result.average_fill_price) if result and result.average_fill_price else None,
                str(result.average_fee_paid) if result and result.average_fee_paid else None,
                error,
            ),
        )
        self._conn.commit()

    def total_filled_cost(self) -> Decimal:
        rows = self._conn.execute(
            "SELECT fill_count, average_fill_price FROM orders"
            " WHERE purpose IN ('entry', 'retry') AND fill_count IS NOT NULL"
        ).fetchall()
        total = Decimal(0)
        for fill_count, average_fill_price in rows:
            if fill_count and average_fill_price:
                total += Decimal(fill_count) * Decimal(average_fill_price)
        return total

    def close(self) -> None:
        self._conn.close()


def _now() -> str:
    return datetime.now(UTC).isoformat()
