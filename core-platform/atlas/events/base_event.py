from dataclasses import dataclass, field
from datetime import datetime

from atlas.core.time import utc_now


@dataclass(frozen=True, kw_only=True)
class BaseEvent:
    timestamp: datetime = field(default_factory=utc_now)
