import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class OutboxEntryType(StrEnum):
    TRADE_RESULT = "TRADE_RESULT"


@dataclass(frozen=True, kw_only=True)
class OutboxEntry:
    entry_type: OutboxEntryType
    # Loose payload typing: outbox events carry mixed scalar/JSON-ish values,
    # not just strings (pnl may be Decimal-as-str, timestamps as int, etc).
    payload: dict[str, Any]


OutboxQueue = asyncio.Queue[OutboxEntry]
