from decimal import Decimal
from urllib.parse import urlparse

import aiohttp

from kalshi_bot.client.auth import RsaRequestSigner
from kalshi_bot.models import OrderRequest, OrderResult

ORDERS_ENDPOINT = "/portfolio/events/orders"


class KalshiApiError(Exception):
    def __init__(self, *, status: int, body: str) -> None:
        super().__init__(f"Kalshi API error {status}: {body}")
        self.status = status
        self.body = body


class KalshiTradingClient:
    def __init__(
        self,
        *,
        base_url: str,
        session: aiohttp.ClientSession,
        signer: RsaRequestSigner,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._signer = signer
        self._sign_path_prefix = urlparse(self._base_url).path

    async def create_order(self, request: OrderRequest) -> OrderResult:
        body = {
            "ticker": request.ticker,
            "side": request.side,
            "count": _fixed(request.count, places=2),
            "price": _fixed(request.price, places=4),
            "time_in_force": request.time_in_force,
            "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": request.client_order_id,
        }
        headers = self._signer.headers(
            method="POST", path=f"{self._sign_path_prefix}{ORDERS_ENDPOINT}"
        )
        async with self._session.post(
            f"{self._base_url}{ORDERS_ENDPOINT}", json=body, headers=headers
        ) as response:
            text = await response.text()
            if response.status >= 400:
                raise KalshiApiError(status=response.status, body=text)
            payload = await response.json()
        return OrderResult(
            order_id=payload.get("order_id", ""),
            client_order_id=payload.get("client_order_id", request.client_order_id),
            fill_count=Decimal(payload.get("fill_count", "0") or "0"),
            remaining_count=Decimal(payload.get("remaining_count", "0") or "0"),
            average_fill_price=_optional_decimal(payload.get("average_fill_price")),
            average_fee_paid=_optional_decimal(payload.get("average_fee_paid")),
        )


def _fixed(value: Decimal, *, places: int) -> str:
    return f"{value:.{places}f}"


def _optional_decimal(raw: str | None) -> Decimal | None:
    return Decimal(raw) if raw not in (None, "") else None
