import asyncio
from dataclasses import dataclass
from enum import StrEnum


class OutboxEntryType(StrEnum):
    TRADE_RESULT = "TRADE_RESULT"


@dataclass(frozen=True, kw_only=True)
class OutboxEntry:
    entry_type: OutboxEntryType
    payload: dict[str, str]


OutboxQueue = asyncio.Queue[OutboxEntry]
