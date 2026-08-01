from decimal import Decimal

from kalshi_bot.backtest.candle import Candle
from kalshi_bot.backtest.history import parse_candle
from kalshi_bot.backtest.replay import replay_event
from kalshi_bot.backtest.report import build_summary, format_summary
from kalshi_bot.models import OpportunityKind

SAMPLE_CANDLE = {
    "end_period_ts": 1785484800,
    "yes_bid": {
        "open_dollars": "0.1200",
        "high_dollars": "0.1200",
        "low_dollars": "0.1100",
        "close_dollars": "0.1200",
    },
    "yes_ask": {
        "open_dollars": "0.1300",
        "high_dollars": "0.1400",
        "low_dollars": "0.1300",
        "close_dollars": "0.1300",
    },
}


def make_candle(
    *,
    end_ts: int,
    yes_bid: str,
    yes_ask: str,
    yes_bid_low: str | None = None,
    yes_ask_high: str | None = None,
) -> Candle:
    return Candle(
        end_ts=end_ts,
        yes_bid_close=Decimal(yes_bid),
        yes_bid_low=Decimal(yes_bid_low or yes_bid),
        yes_ask_close=Decimal(yes_ask),
        yes_ask_high=Decimal(yes_ask_high or yes_ask),
    )


def test_parse_candle_from_live_payload_shape():
    candle = parse_candle(SAMPLE_CANDLE)
    assert candle is not None
    assert candle.end_ts == 1785484800
    assert candle.yes_bid_close == Decimal("0.1200")
    assert candle.yes_bid_low == Decimal("0.1100")
    assert candle.yes_ask_high == Decimal("0.1400")


def test_parse_candle_rejects_missing_quotes():
    assert parse_candle({"end_period_ts": 1, "yes_bid": {}, "yes_ask": {}}) is None


def test_replay_detects_no_basket_on_aligned_bars(config):
    # yes_bid 0.40 → NO ask 0.60 × 3 = 1.80 < 2 − fees
    candles = {
        f"EVT-{i}": [
            make_candle(end_ts=100, yes_bid="0.40", yes_ask="0.45"),
            make_candle(end_ts=200, yes_bid="0.30", yes_ask="0.35"),
        ]
        for i in range(3)
    }
    result = replay_event(
        event_ticker="EVT",
        title="t",
        mutually_exclusive=True,
        candles_by_market=candles,
        config=config,
        mode="close",
    )
    assert result.bars_replayed == 2
    basket_hits = [
        h for h in result.hits if h.opportunity.kind == OpportunityKind.NO_BASKET
    ]
    assert [h.ts for h in basket_hits] == [100]


def test_replay_conservative_mode_uses_worst_quotes(config):
    # close 기준으로는 기회지만 bar 저가(yes_bid_low) 기준으로는 아님
    candles = {
        f"EVT-{i}": [
            make_candle(
                end_ts=100, yes_bid="0.40", yes_ask="0.45",
                yes_bid_low="0.30", yes_ask_high="0.50",
            )
        ]
        for i in range(3)
    }
    close_result = replay_event(
        event_ticker="EVT", title="t", mutually_exclusive=True,
        candles_by_market=candles, config=config, mode="close",
    )
    conservative_result = replay_event(
        event_ticker="EVT", title="t", mutually_exclusive=True,
        candles_by_market=candles, config=config, mode="conservative",
    )
    assert any(
        h.opportunity.kind == OpportunityKind.NO_BASKET for h in close_result.hits
    )
    assert not any(
        h.opportunity.kind == OpportunityKind.NO_BASKET
        for h in conservative_result.hits
    )


def test_replay_requires_all_legs_present(config):
    candles = {
        "EVT-0": [make_candle(end_ts=100, yes_bid="0.40", yes_ask="0.45")],
        "EVT-1": [],
    }
    result = replay_event(
        event_ticker="EVT", title="t", mutually_exclusive=True,
        candles_by_market=candles, config=config, mode="close",
    )
    assert result.bars_replayed == 0
    assert result.hits == ()


def test_summary_aggregates_hits(config):
    candles = {
        f"EVT-{i}": [make_candle(end_ts=100, yes_bid="0.40", yes_ask="0.45")]
        for i in range(3)
    }
    result = replay_event(
        event_ticker="EVT", title="t", mutually_exclusive=True,
        candles_by_market=candles, config=config, mode="close",
    )
    summary = build_summary([result])
    assert summary["events_replayed"] == 1
    assert summary["kinds"]["no_basket"]["bar_hits"] == 1
    assert "no_basket" in format_summary(summary)
