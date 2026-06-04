import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

Handler = Callable[[Any], Coroutine[Any, Any, None]]

_log = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: Any) -> None:
        handlers = self._handlers[type(event)]
        if not handlers:
            return
        # Run handlers concurrently and isolate failures: a buggy subscriber
        # must not block the rest of the fan-out.
        results = await asyncio.gather(*(h(event) for h in handlers), return_exceptions=True)
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                _log.exception("event bus handler %r failed", handler, exc_info=result)
