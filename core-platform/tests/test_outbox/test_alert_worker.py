import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from atlas.outbox.queue import OutboxEntry, OutboxEntryType, OutboxQueue
from atlas.outbox.workers import AlertWorker

_WEBHOOK = "https://discord.fake/webhook"


def _make_entry(state: str, arb_id: str = "abc123", pnl: str = "1.23") -> OutboxEntry:
    return OutboxEntry(
        entry_type=OutboxEntryType.TRADE_RESULT,
        payload={"state": state, "arb_id": arb_id, "net_pnl": pnl},
    )


def _mock_session():
    mock_resp = MagicMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_sess = MagicMock()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=False)
    mock_sess.post = MagicMock(return_value=mock_resp)
    return mock_sess


async def _run_worker_once(worker: AlertWorker, mock_sess: MagicMock) -> None:
    with patch("aiohttp.ClientSession", return_value=mock_sess):
        task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def test_posts_on_complete():
    queue: OutboxQueue = asyncio.Queue()
    worker = AlertWorker(queue=queue, webhook_url=_WEBHOOK)
    await queue.put(_make_entry("COMPLETE"))

    sess = _mock_session()
    await _run_worker_once(worker, sess)

    sess.post.assert_called_once()


async def test_posts_on_unwind_complete():
    queue: OutboxQueue = asyncio.Queue()
    worker = AlertWorker(queue=queue, webhook_url=_WEBHOOK)
    await queue.put(_make_entry("UNWIND_COMPLETE"))

    sess = _mock_session()
    await _run_worker_once(worker, sess)

    sess.post.assert_called_once()


async def test_posts_on_failed():
    queue: OutboxQueue = asyncio.Queue()
    worker = AlertWorker(queue=queue, webhook_url=_WEBHOOK)
    await queue.put(_make_entry("FAILED"))

    sess = _mock_session()
    await _run_worker_once(worker, sess)

    sess.post.assert_called_once()


async def test_skips_non_trade_result_entry():
    queue: OutboxQueue = asyncio.Queue()
    worker = AlertWorker(queue=queue, webhook_url=_WEBHOOK)
    # OutboxEntryType에 존재하지 않는 타입을 직접 문자열로 흉내낼 수 없으므로
    # 유효하지 않은 state로 TRADE_RESULT를 넣어 스킵 동작 검증
    await queue.put(
        OutboxEntry(
            entry_type=OutboxEntryType.TRADE_RESULT,
            payload={"state": "LEG1_PENDING", "arb_id": "x"},
        )
    )

    sess = _mock_session()
    await _run_worker_once(worker, sess)

    sess.post.assert_not_called()


async def test_skips_irrelevant_state():
    queue: OutboxQueue = asyncio.Queue()
    worker = AlertWorker(queue=queue, webhook_url=_WEBHOOK)
    await queue.put(_make_entry("LEG2_FILLED"))

    sess = _mock_session()
    await _run_worker_once(worker, sess)

    sess.post.assert_not_called()


async def test_webhook_url_passed_correctly():
    queue: OutboxQueue = asyncio.Queue()
    worker = AlertWorker(queue=queue, webhook_url=_WEBHOOK)
    await queue.put(_make_entry("COMPLETE"))

    sess = _mock_session()
    await _run_worker_once(worker, sess)

    call_args = sess.post.call_args
    assert call_args[0][0] == _WEBHOOK


async def test_message_contains_arb_id_and_pnl():
    queue: OutboxQueue = asyncio.Queue()
    worker = AlertWorker(queue=queue, webhook_url=_WEBHOOK)
    await queue.put(_make_entry("COMPLETE", arb_id="xyz999", pnl="3.14"))

    sess = _mock_session()
    await _run_worker_once(worker, sess)

    content = sess.post.call_args[1]["json"]["content"]
    assert "xyz999" in content
    assert "3.14" in content


async def test_multiple_entries_only_notifiable_posted():
    queue: OutboxQueue = asyncio.Queue()
    worker = AlertWorker(queue=queue, webhook_url=_WEBHOOK)
    await queue.put(_make_entry("LEG1_PENDING"))
    await queue.put(_make_entry("COMPLETE"))
    await queue.put(_make_entry("LEG2_FILLED"))

    sess = _mock_session()
    with patch("aiohttp.ClientSession", return_value=sess):
        task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert sess.post.call_count == 1
