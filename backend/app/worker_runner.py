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


async def run_worker(queue_name: str) -> None:
    """Run a single worker, handling exceptions locally."""
    worker = create_worker(WorkerSettings, queue_name=queue_name)
    try:
        await worker.async_run()
    except Exception as e:
        import logging
        logging.error(f"Worker {queue_name} failed: {e}", exc_info=True)
        raise


async def main() -> None:
    workers = [run_worker(q) for q in WorkerSettings.queues]
    # Use return_exceptions=True to prevent one failure from cancelling others
    results = await asyncio.gather(*workers, return_exceptions=True)
    
    # Check for exceptions
    for queue_name, result in zip(WorkerSettings.queues, results):
        if isinstance(result, Exception):
            import logging
            logging.error(f"Worker {queue_name} failed permanently: {result}", exc_info=result)


if __name__ == "__main__":
    asyncio.run(main())
