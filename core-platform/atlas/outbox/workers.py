import logging

import aiohttp

from atlas.outbox.queue import OutboxEntryType, OutboxQueue

_log = logging.getLogger(__name__)
_NOTIFY_STATES = {"COMPLETE", "UNWIND_COMPLETE", "FAILED"}


class AlertWorker:
    """
    Consumes outbox entries and forwards trade results to:
      - a Discord webhook (`webhook_url`) for human-visible alerts
      - the api-server's internal HTTP endpoint (`http_url`) for fan-out to
        WebSocket-connected dashboards
    Either, both, or neither destination can be configured; the worker simply
    skips disabled destinations.
    """

    def __init__(
        self,
        queue: OutboxQueue,
        webhook_url: str | None = None,
        http_url: str | None = None,
    ) -> None:
        self._queue = queue
        self._webhook_url = webhook_url
        self._http_url = http_url

    async def run(self) -> None:
        while True:
            entry = await self._queue.get()
            if entry.entry_type != OutboxEntryType.TRADE_RESULT:
                continue
            if entry.payload.get("state") not in _NOTIFY_STATES:
                continue
            if self._webhook_url:
                await self._post_discord(entry.payload)
            if self._http_url:
                await self._post_http(entry.payload)

    async def _post_discord(self, payload: dict) -> None:
        state = payload.get("state", "")
        arb_id = payload.get("arb_id", "")
        pnl = payload.get("net_pnl", "N/A")
        content = f"**[Atlas Trading]** `{state}` | arb_id: `{arb_id}` | PnL: `{pnl}`"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self._webhook_url, json={"content": content}):
                    pass
        except Exception:
            _log.exception("discord webhook post failed")

    async def _post_http(self, payload: dict) -> None:
        # Internal HTTP destination receives the raw payload so the api-server
        # can broadcast it verbatim to WebSocket clients.
        body = {
            "type": payload.get("state", ""),
            "arb_id": payload.get("arb_id", ""),
            "pnl": payload.get("net_pnl"),
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self._http_url, json=body):
                    pass
        except Exception:
            _log.exception("internal alert post failed")
