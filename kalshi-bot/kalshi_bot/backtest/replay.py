from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from kalshi_bot.backtest.candle import Candle
from kalshi_bot.config import BotConfig
from kalshi_bot.models import EventSnapshot, MarketQuote, Opportunity
from kalshi_bot.scanner import detect

QuoteMode = Literal["close", "conservative"]


@dataclass(frozen=True, kw_only=True)
class BacktestHit:
    ts: int
    opportunity: Opportunity


@dataclass(frozen=True, kw_only=True)
class EventReplayResult:
    event_ticker: str
    bars_replayed: int
    hits: tuple[BacktestHit, ...]


def replay_event(
    *,
    event_ticker: str,
    title: str,
    mutually_exclusive: bool,
    candles_by_market: dict[str, list[Candle]],
    config: BotConfig,
    mode: QuoteMode,
) -> EventReplayResult:
    """레그별 캔들을 타임스탬프로 정렬해 스캐너를 과거 시점마다 재생한다.

    과거 호가 잔량은 알 수 없으므로 모든 레그 잔량을 max_count로 가정한다 —
    결과는 체결 가능성의 상한 추정이다.
    """
    indexed = {
        ticker: {candle.end_ts: candle for candle in candles}
        for ticker, candles in candles_by_market.items()
    }
    if not indexed or any(not candles for candles in indexed.values()):
        return EventReplayResult(event_ticker=event_ticker, bars_replayed=0, hits=())
    common_ts = sorted(set.intersection(*(set(c) for c in indexed.values())))
    synthetic_size = config.max_count_per_opportunity
    hits: list[BacktestHit] = []
    for ts in common_ts:
        markets = tuple(
            _quote_from_candle(
                ticker=ticker, candle=indexed[ticker][ts], mode=mode, size=synthetic_size
            )
            for ticker in indexed
        )
        snapshot = EventSnapshot(
            event_ticker=event_ticker,
            title=title,
            mutually_exclusive=mutually_exclusive,
            markets=markets,
        )
        for opportunity in detect(snapshot, config):
            hits.append(BacktestHit(ts=ts, opportunity=opportunity))
    return EventReplayResult(
        event_ticker=event_ticker, bars_replayed=len(common_ts), hits=tuple(hits)
    )


def _quote_from_candle(
    *, ticker: str, candle: Candle, mode: QuoteMode, size: Decimal
) -> MarketQuote:
    if mode == "close":
        yes_bid, yes_ask = candle.yes_bid_close, candle.yes_ask_close
    else:
        yes_bid, yes_ask = candle.yes_bid_low, candle.yes_ask_high
    return MarketQuote(
        ticker=ticker,
        status="active",
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        yes_bid_size=size,
        yes_ask_size=size,
    )
