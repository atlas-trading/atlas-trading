import asyncio
import logging
import uuid
from decimal import Decimal

from kalshi_bot.client import KalshiApiError, KalshiPublicClient, KalshiTradingClient
from kalshi_bot.models import Opportunity, OpportunityLeg, OrderRequest, OrderResult
from kalshi_bot.store import Store

logger = logging.getLogger(__name__)

MIN_PRICE = Decimal("0.01")
MAX_PRICE = Decimal("0.99")


class BasketExecutor:
    """탐지된 기회를 N-레그 IOC 지정가로 실행한다.

    부분 체결 시 잔여 수량을 1회 재시도하고, 그래도 레그 간 체결량이 어긋나면
    초과 체결분을 반대 방향 IOC로 언와인드한다.
    """

    def __init__(
        self,
        *,
        trading: KalshiTradingClient,
        public: KalshiPublicClient,
        store: Store,
        max_total_exposure: Decimal,
    ) -> None:
        self._trading = trading
        self._public = public
        self._store = store
        self._max_total_exposure = max_total_exposure

    async def execute(self, opportunity: Opportunity, opportunity_id: int) -> bool:
        if not opportunity.executable:
            return False
        cost = sum((leg.price for leg in opportunity.legs), Decimal(0)) * opportunity.count
        if self._store.total_filled_cost() + cost > self._max_total_exposure:
            logger.warning("skip %s: exposure limit", opportunity.event_ticker)
            return False
        if not await self._requote_ok(opportunity):
            logger.info("skip %s: requote failed", opportunity.event_ticker)
            return False

        fills = await self._place_all_legs(opportunity, opportunity_id)
        fills = await self._retry_shortfalls(opportunity, opportunity_id, fills)
        min_fill = min(fills.values())
        await self._unwind_excess(opportunity, opportunity_id, fills, min_fill)
        fully_filled = min_fill >= opportunity.count
        logger.info(
            "executed %s: min_fill=%s target=%s", opportunity.event_ticker,
            min_fill, opportunity.count,
        )
        return fully_filled

    async def _requote_ok(self, opportunity: Opportunity) -> bool:
        quotes = await asyncio.gather(
            *(self._public.get_market(leg.ticker) for leg in opportunity.legs)
        )
        for leg, quote in zip(opportunity.legs, quotes, strict=True):
            if quote is None:
                return False
            price = quote.no_ask if leg.side == "no" else quote.yes_ask
            size = quote.no_ask_size if leg.side == "no" else quote.yes_ask_size
            if price > leg.price or size < opportunity.count:
                return False
        return True

    async def _place_all_legs(
        self, opportunity: Opportunity, opportunity_id: int
    ) -> dict[str, Decimal]:
        results = await asyncio.gather(
            *(
                self._place(leg, count=opportunity.count, opportunity_id=opportunity_id,
                            purpose="entry")
                for leg in opportunity.legs
            )
        )
        return {
            leg.ticker: result.fill_count if result else Decimal(0)
            for leg, result in zip(opportunity.legs, results, strict=True)
        }

    async def _retry_shortfalls(
        self,
        opportunity: Opportunity,
        opportunity_id: int,
        fills: dict[str, Decimal],
    ) -> dict[str, Decimal]:
        updated = dict(fills)
        for leg in opportunity.legs:
            shortfall = opportunity.count - updated[leg.ticker]
            if shortfall <= 0:
                continue
            result = await self._place(
                leg, count=shortfall, opportunity_id=opportunity_id, purpose="retry"
            )
            if result is not None:
                updated[leg.ticker] += result.fill_count
        return updated

    async def _unwind_excess(
        self,
        opportunity: Opportunity,
        opportunity_id: int,
        fills: dict[str, Decimal],
        min_fill: Decimal,
    ) -> None:
        for leg in opportunity.legs:
            excess = fills[leg.ticker] - min_fill
            if excess <= 0:
                continue
            quote = await self._public.get_market(leg.ticker)
            if quote is None:
                self._store.record_order(
                    opportunity_id=opportunity_id, ticker=leg.ticker, side="unwind",
                    price=Decimal(0), count=excess, purpose="unwind",
                    error="no quote for unwind",
                )
                continue
            if leg.side == "no":
                side, price = "bid", min(quote.yes_ask, MAX_PRICE)
            else:
                side, price = "ask", max(quote.yes_bid, MIN_PRICE)
            request = OrderRequest(
                ticker=leg.ticker,
                side=side,
                price=price,
                count=excess,
                time_in_force="immediate_or_cancel",
                client_order_id=str(uuid.uuid4()),
            )
            await self._send(request, opportunity_id=opportunity_id, purpose="unwind")

    async def _place(
        self,
        leg: OpportunityLeg,
        *,
        count: Decimal,
        opportunity_id: int,
        purpose: str,
    ) -> OrderResult | None:
        side = "bid" if leg.side == "yes" else "ask"
        price = leg.price if leg.side == "yes" else Decimal(1) - leg.price
        request = OrderRequest(
            ticker=leg.ticker,
            side=side,
            price=price,
            count=count,
            time_in_force="immediate_or_cancel",
            client_order_id=str(uuid.uuid4()),
        )
        return await self._send(request, opportunity_id=opportunity_id, purpose=purpose)

    async def _send(
        self, request: OrderRequest, *, opportunity_id: int, purpose: str
    ) -> OrderResult | None:
        try:
            result = await self._trading.create_order(request)
        except KalshiApiError as exc:
            logger.error("order failed %s %s: %s", request.ticker, purpose, exc)
            self._store.record_order(
                opportunity_id=opportunity_id, ticker=request.ticker, side=request.side,
                price=request.price, count=request.count, purpose=purpose, error=str(exc),
            )
            return None
        self._store.record_order(
            opportunity_id=opportunity_id, ticker=request.ticker, side=request.side,
            price=request.price, count=request.count, purpose=purpose, result=result,
        )
        return result
