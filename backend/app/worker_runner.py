"""Multi-queue worker runner.

arq's CLI runs a single queue per process; this entrypoint runs one Worker
per priority queue (urgent/normal/bulk) inside a single event loop, so one
container serves every priority while urgent jobs still drain first.

Usage: python -m app.worker_runner
"""

from __future__ import annotations

import asyncio

from arq.worker import create_worker

from app.core.worker import WorkerSettings


async def main() -> None:
    workers = [create_worker(WorkerSettings, queue_name=q) for q in WorkerSettings.queues]
    await asyncio.gather(*(w.async_run() for w in workers))


if __name__ == "__main__":
    asyncio.run(main())
