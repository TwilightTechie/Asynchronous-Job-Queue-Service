import asyncio
import uuid

from app.queue import AsyncioJobQueue


def test_put_nowait_then_get_returns_the_job_id():
    queue = AsyncioJobQueue()
    job_id = uuid.uuid4()

    queue.put_nowait(job_id)

    assert asyncio.run(queue.get()) == job_id


def test_get_waits_for_an_item_to_be_put():
    queue = AsyncioJobQueue()
    job_id = uuid.uuid4()

    async def scenario():
        get_task = asyncio.create_task(queue.get())
        await asyncio.sleep(0)
        queue.put_nowait(job_id)
        return await get_task

    assert asyncio.run(scenario()) == job_id


def test_qsize_reflects_pending_items():
    queue = AsyncioJobQueue()
    assert queue.qsize() == 0

    queue.put_nowait(uuid.uuid4())
    queue.put_nowait(uuid.uuid4())
    assert queue.qsize() == 2

    asyncio.run(queue.get())
    assert queue.qsize() == 1
