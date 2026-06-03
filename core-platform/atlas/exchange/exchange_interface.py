from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine

from atlas.core.trading_pair import TradingPair
from atlas.execution.order import Order

TickerCallback = Callable[[dict], Coroutine[Any, Any, None]]


class ExchangeInterface(ABC):
    @abstractmethod
    async def place_order(self, order: Order) -> Order: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> None: ...

    @abstractmethod
    async def get_balance(self) -> dict[str, Any]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    @abstractmethod
    async def subscribe_ticker(
        self, trading_pairs: list[TradingPair], callback: TickerCallback
    ) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
