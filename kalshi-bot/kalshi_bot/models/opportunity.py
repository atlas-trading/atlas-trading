from dataclasses import dataclass
from decimal import Decimal

from kalshi_bot.models.opportunity_kind import OpportunityKind
from kalshi_bot.models.opportunity_leg import OpportunityLeg


@dataclass(frozen=True, kw_only=True)
class Opportunity:
    kind: OpportunityKind
    event_ticker: str
    legs: tuple[OpportunityLeg, ...]
    count: Decimal
    gross_edge_total: Decimal
    fee_total: Decimal
    net_edge_total: Decimal
    executable: bool

    @property
    def net_edge_per_contract(self) -> Decimal:
        return self.net_edge_total / self.count
