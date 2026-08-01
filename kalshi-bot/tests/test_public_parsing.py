from decimal import Decimal

from kalshi_bot.client.public import _parse_event, _parse_market

SAMPLE_MARKET = {
    "ticker": "KXELONMARS-99",
    "market_type": "binary",
    "status": "active",
    "yes_bid_dollars": "0.1200",
    "yes_ask_dollars": "0.1300",
    "yes_bid_size_fp": "129.37",
    "yes_ask_size_fp": "1650.72",
}


def test_parse_market_from_live_payload_shape():
    quote = _parse_market(SAMPLE_MARKET)
    assert quote is not None
    assert quote.yes_bid == Decimal("0.1200")
    assert quote.yes_ask == Decimal("0.1300")
    assert quote.no_ask == Decimal("0.8800")
    assert quote.no_ask_size == Decimal("129.37")
    assert quote.status == "active"


def test_parse_market_defaults_when_quotes_missing():
    quote = _parse_market({"ticker": "T", "market_type": "binary", "status": "active"})
    assert quote is not None
    assert quote.yes_bid == Decimal(0)
    assert quote.yes_ask == Decimal(1)
    assert quote.yes_bid_size == Decimal(0)


def test_parse_market_rejects_non_binary():
    assert _parse_market({"ticker": "T", "market_type": "scalar"}) is None


def test_parse_event_collects_markets_and_flags():
    event = _parse_event(
        {
            "event_ticker": "KXELONMARS",
            "title": "Elon to Mars",
            "mutually_exclusive": True,
            "markets": [SAMPLE_MARKET, {"ticker": "BAD", "market_type": "scalar"}],
        }
    )
    assert event is not None
    assert event.mutually_exclusive
    assert len(event.markets) == 1
