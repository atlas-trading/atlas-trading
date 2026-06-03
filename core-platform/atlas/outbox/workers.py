import aiohttp

from atlas.outbox.queue import OutboxEntryType, OutboxQueue

_NOTIFY_STATES = {"COMPLETE", "UNWIND_COMPLETE", "FAILED"}


class AlertWorker:
    def __init__(self, queue: OutboxQueue, webhook_url: str) -> None:
        self._queue = queue
        self._webhook_url = webhook_url

    async def run(self) -> None:
        while True:
            entry = await self._queue.get()
            if entry.entry_type != OutboxEntryType.TRADE_RESULT:
                continue
            if entry.payload.get("state") not in _NOTIFY_STATES:
                continue
            await self._post(entry.payload)

    async def _post(self, payload: dict[str, str]) -> None:
        state = payload.get("state", "")
        arb_id = payload.get("arb_id", "")
        pnl = payload.get("net_pnl", "N/A")
        content = f"**[Atlas Trading]** `{state}` | arb_id: `{arb_id}` | PnL: `{pnl}`"
        async with aiohttp.ClientSession() as session:
            async with session.post(self._webhook_url, json={"content": content}):
                pass
