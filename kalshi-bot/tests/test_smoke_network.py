import aiohttp
import pytest

from kalshi_bot.client.public import KalshiPublicClient
from kalshi_bot.config import PUBLIC_BASE_URLS


@pytest.mark.network
async def test_live_prod_events_parse():
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        client = KalshiPublicClient(base_url=PUBLIC_BASE_URLS["prod"], session=session)
        events = await client.list_open_events(max_pages=1)
    assert events
    assert any(event.markets for event in events)
