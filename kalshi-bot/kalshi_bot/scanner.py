from decimal import Decimal

from kalshi_bot.config import BotConfig
from kalshi_bot.fees import taker_fee
from kalshi_bot.models import (
    EventSnapshot,
    MarketQuote,
    Opportunity,
    OpportunityKind,
    OpportunityLeg,
)

ONE = Decimal(1)


def detect(event: EventSnapshot, config: BotConfig) -> list[Opportunity]:
    active = [m for m in event.markets if m.status == "active"]
    opportunities = []
    for market in active:
        single = _detect_single_market_complement(event, market, config)
        if single is not None:
            opportunities.append(single)
    if event.mutually_exclusive and len(active) >= 2:
        no_basket = _detect_no_basket(event, active, config)
        if no_basket is not None:
            opportunities.append(no_basket)
        yes_anomaly = _detect_yes_sum_anomaly(event, active, config)
        if yes_anomaly is not None:
            opportunities.append(yes_anomaly)
    return opportunities


def _detect_single_market_complement(
    event: EventSnapshot, market: MarketQuote, config: BotConfig
) -> Opportunity | None:
    if market.yes_ask >= ONE or market.no_ask >= ONE:
        return None
    if market.yes_ask_size <= 0 or market.no_ask_size <= 0:
        return None
    gross_per_contract = ONE - (market.yes_ask + market.no_ask)
    if gross_per_contract <= 0:
        return None
    count = min(market.yes_ask_size, market.no_ask_size, config.max_count_per_opportunity)
    legs = (
        OpportunityLeg(
            ticker=market.ticker,
            side="yes",
            price=market.yes_ask,
            available_size=market.yes_ask_size,
        ),
        OpportunityLeg(
            ticker=market.ticker,
            side="no",
            price=market.no_ask,
            available_size=market.no_ask_size,
        ),
    )
    return _build_opportunity(
        kind=OpportunityKind.SINGLE_MARKET_COMPLEMENT,
        event_ticker=event.event_ticker,
        legs=legs,
        count=count,
        gross_per_contract=gross_per_contract,
        config=config,
        allow_execution=True,
    )


def _detect_no_basket(
    event: EventSnapshot, markets: list[MarketQuote], config: BotConfig
) -> Opportunity | None:
    if any(m.no_ask >= ONE or m.no_ask_size <= 0 for m in markets):
        return None
    total_cost = sum((m.no_ask for m in markets), Decimal(0))
    gross_per_contract = Decimal(len(markets) - 1) - total_cost
    if gross_per_contract <= 0:
        return None
    count = min(
        min(m.no_ask_size for m in markets),
        config.max_count_per_opportunity,
    )
    legs = tuple(
        OpportunityLeg(
            ticker=m.ticker, side="no", price=m.no_ask, available_size=m.no_ask_size
        )
        for m in markets
    )
    return _build_opportunity(
        kind=OpportunityKind.NO_BASKET,
        event_ticker=event.event_ticker,
        legs=legs,
        count=count,
        gross_per_contract=gross_per_contract,
        config=config,
        allow_execution=True,
    )


def _detect_yes_sum_anomaly(
    event: EventSnapshot, markets: list[MarketQuote], config: BotConfig
) -> Opportunity | None:
    """Σ(YES ask) < 1 후보. 이벤트 전수성(exhaustiveness)을 API로 확인할 수 없어
    무위험이 보장되지 않으므로 기록만 하고 절대 자동 실행하지 않는다."""
    if any(m.yes_ask >= ONE or m.yes_ask_size <= 0 for m in markets):
        return None
    total_cost = sum((m.yes_ask for m in markets), Decimal(0))
    gross_per_contract = ONE - total_cost
    if gross_per_contract <= 0:
        return None
    count = min(
        min(m.yes_ask_size for m in markets),
        config.max_count_per_opportunity,
    )
    legs = tuple(
        OpportunityLeg(
            ticker=m.ticker, side="yes", price=m.yes_ask, available_size=m.yes_ask_size
        )
        for m in markets
    )
    return _build_opportunity(
        kind=OpportunityKind.YES_SUM_ANOMALY,
        event_ticker=event.event_ticker,
        legs=legs,
        count=count,
        gross_per_contract=gross_per_contract,
        config=config,
        allow_execution=False,
    )


def _build_opportunity(
    *,
    kind: OpportunityKind,
    event_ticker: str,
    legs: tuple[OpportunityLeg, ...],
    count: Decimal,
    gross_per_contract: Decimal,
    config: BotConfig,
    allow_execution: bool,
) -> Opportunity | None:
    if count <= 0:
        return None
    fee_total = sum(
        (taker_fee(price=leg.price, count=count, coef=config.fee_coef) for leg in legs),
        Decimal(0),
    )
    gross_total = gross_per_contract * count
    net_total = gross_total - fee_total
    if net_total / count < config.min_net_edge_per_contract:
        return None
    return Opportunity(
        kind=kind,
        event_ticker=event_ticker,
        legs=legs,
        count=count,
        gross_edge_total=gross_total,
        fee_total=fee_total,
        net_edge_total=net_total,
        executable=allow_execution,
    )
