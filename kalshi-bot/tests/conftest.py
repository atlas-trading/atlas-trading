from decimal import Decimal
from pathlib import Path

import pytest

from kalshi_bot.config import BotConfig
from kalshi_bot.models import MarketQuote


@pytest.fixture
def config() -> BotConfig:
    return BotConfig(
        env="demo",
        api_key_id=None,
        private_key_path=None,
        poll_interval_seconds=5.0,
        db_path=Path(":memory:"),
        min_net_edge_per_contract=Decimal("0.01"),
        max_count_per_opportunity=Decimal("10"),
        max_total_exposure=Decimal("100"),
        fee_coef=Decimal("0.07"),
    )


def make_quote(
    *,
    ticker: str = "TEST-A",
    status: str = "active",
    yes_bid: str = "0.40",
    yes_ask: str = "0.45",
    yes_bid_size: str = "50",
    yes_ask_size: str = "50",
) -> MarketQuote:
    return MarketQuote(
        ticker=ticker,
        status=status,
        yes_bid=Decimal(yes_bid),
        yes_ask=Decimal(yes_ask),
        yes_bid_size=Decimal(yes_bid_size),
        yes_ask_size=Decimal(yes_ask_size),
    )
