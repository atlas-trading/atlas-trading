from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine

from atlas.core.trading_pair import TradingPair
from atlas.exchange.order_result import OrderResult
from atlas.execution.balance import Balance
from atlas.execution.order import Order

TickerCallback = Callable[[dict], Coroutine[Any, Any, None]]


class ExchangeInterface(ABC):
    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult: ...

    @abstractmethod
    async def cancel_order(self, order: Order) -> None: ...

    @abstractmethod
    async def get_balance(self) -> Balance: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    @abstractmethod
    async def subscribe_ticker(
        self, trading_pairs: list[TradingPair], callback: TickerCallback
    ) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
