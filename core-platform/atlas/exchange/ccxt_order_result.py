from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class CcxtOrderResult:
    id: str
    status: str
