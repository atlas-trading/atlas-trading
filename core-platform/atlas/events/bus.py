from collections import defaultdict
from typing import Any, Callable, Coroutine

Handler = Callable[[Any], Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: Any) -> None:
        for handler in self._handlers[type(event)]:
            await handler(event)
