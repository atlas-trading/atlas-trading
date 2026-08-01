from decimal import Decimal, InvalidOperation

import aiohttp

from kalshi_bot.models import EventSnapshot, MarketQuote


class KalshiPublicClient:
    """인증 불필요한 마켓 데이터 조회."""

    def __init__(self, *, base_url: str, session: aiohttp.ClientSession) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session

    async def list_open_events(self, *, max_pages: int | None = None) -> list[EventSnapshot]:
        events: list[EventSnapshot] = []
        cursor: str | None = None
        pages = 0
        while True:
            params = {"status": "open", "with_nested_markets": "true", "limit": "200"}
            if cursor:
                params["cursor"] = cursor
            async with self._session.get(
                f"{self._base_url}/events", params=params
            ) as response:
                response.raise_for_status()
                payload = await response.json()
            for event_data in payload.get("events", []):
                snapshot = _parse_event(event_data)
                if snapshot is not None:
                    events.append(snapshot)
            cursor = payload.get("cursor")
            pages += 1
            if not cursor or (max_pages is not None and pages >= max_pages):
                return events

    async def get_market(self, ticker: str) -> MarketQuote | None:
        async with self._session.get(f"{self._base_url}/markets/{ticker}") as response:
            response.raise_for_status()
            payload = await response.json()
        return _parse_market(payload.get("market", {}))


def _parse_event(data: dict) -> EventSnapshot | None:
    event_ticker = data.get("event_ticker")
    if not event_ticker:
        return None
    markets = tuple(
        quote
        for market_data in data.get("markets", [])
        if (quote := _parse_market(market_data)) is not None
    )
    return EventSnapshot(
        event_ticker=event_ticker,
        title=data.get("title", ""),
        mutually_exclusive=bool(data.get("mutually_exclusive", False)),
        markets=markets,
    )


def _parse_market(data: dict) -> MarketQuote | None:
    ticker = data.get("ticker")
    if not ticker or data.get("market_type") != "binary":
        return None
    try:
        return MarketQuote(
            ticker=ticker,
            status=data.get("status", ""),
            yes_bid=_decimal(data, "yes_bid_dollars", default="0"),
            yes_ask=_decimal(data, "yes_ask_dollars", default="1"),
            yes_bid_size=_decimal(data, "yes_bid_size_fp", default="0"),
            yes_ask_size=_decimal(data, "yes_ask_size_fp", default="0"),
        )
    except InvalidOperation:
        return None


def _decimal(data: dict, key: str, *, default: str) -> Decimal:
    raw = data.get(key)
    return Decimal(raw if raw not in (None, "") else default)
