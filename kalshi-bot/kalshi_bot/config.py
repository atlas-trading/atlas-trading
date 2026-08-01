import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

PUBLIC_BASE_URLS = {
    "prod": "https://api.elections.kalshi.com/trade-api/v2",
    "demo": "https://demo-api.kalshi.co/trade-api/v2",
}
TRADING_BASE_URLS = {
    "prod": "https://external-api.kalshi.com/trade-api/v2",
    "demo": "https://demo-api.kalshi.co/trade-api/v2",
}


@dataclass(frozen=True, kw_only=True)
class BotConfig:
    env: str
    api_key_id: str | None
    private_key_path: Path | None
    poll_interval_seconds: float
    db_path: Path
    min_net_edge_per_contract: Decimal
    max_count_per_opportunity: Decimal
    max_total_exposure: Decimal
    fee_coef: Decimal

    @property
    def public_base_url(self) -> str:
        return PUBLIC_BASE_URLS[self.env]

    @property
    def trading_base_url(self) -> str:
        return TRADING_BASE_URLS[self.env]


def load_config(*, env: str | None = None) -> BotConfig:
    resolved_env = env or os.environ.get("KALSHI_ENV", "prod")
    if resolved_env not in PUBLIC_BASE_URLS:
        raise ValueError(f"unknown KALSHI_ENV: {resolved_env}")
    key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH")
    return BotConfig(
        env=resolved_env,
        api_key_id=os.environ.get("KALSHI_API_KEY_ID"),
        private_key_path=Path(key_path) if key_path else None,
        poll_interval_seconds=float(os.environ.get("KALSHI_POLL_INTERVAL", "5")),
        db_path=Path(os.environ.get("KALSHI_DB_PATH", "kalshi_bot.sqlite3")),
        min_net_edge_per_contract=Decimal(os.environ.get("KALSHI_MIN_NET_EDGE", "0.01")),
        max_count_per_opportunity=Decimal(os.environ.get("KALSHI_MAX_COUNT", "10")),
        max_total_exposure=Decimal(os.environ.get("KALSHI_MAX_EXPOSURE", "100")),
        fee_coef=Decimal(os.environ.get("KALSHI_FEE_COEF", "0.07")),
    )
