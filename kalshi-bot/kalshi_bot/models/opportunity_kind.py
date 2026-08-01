from enum import StrEnum


class OpportunityKind(StrEnum):
    SINGLE_MARKET_COMPLEMENT = "single_market_complement"
    NO_BASKET = "no_basket"
    YES_SUM_ANOMALY = "yes_sum_anomaly"
