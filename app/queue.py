import asyncio
from typing import Protocol
from uuid import UUID


class JobQueue(Protocol):
    def put_nowait(self, job_id: UUID) -> None: ...

    async def get(self) -> UUID: ...

    def qsize(self) -> int: ...


class AsyncioJobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[UUID] = asyncio.Queue()

    def put_nowait(self, job_id: UUID) -> None:
        self._queue.put_nowait(job_id)

    async def get(self) -> UUID:
        return await self._queue.get()

    def qsize(self) -> int:
        return self._queue.qsize()
