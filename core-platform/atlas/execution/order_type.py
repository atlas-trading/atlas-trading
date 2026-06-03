from enum import StrEnum


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    FOK = "fok"  # Fill or Kill
