"""
Background worker that retries queued cloud sync items from Redis.
"""

import logging
import threading
import time
from collections.abc import Callable

from config import Config
from offline_store import offline_store

logger = logging.getLogger(__name__)

_worker_started = False
_worker_lock = threading.Lock()


def process_sync_queue(sync_fn: Callable[[dict], bool], batch_size: int) -> dict:
    attempted = 0
    synced = 0

    for _ in range(max(1, batch_size)):
        item = offline_store.peek_sync_reading()
        if item is None:
            break

        attempted += 1
        if sync_fn(item):
            offline_store.pop_sync_reading()
            synced += 1
        else:
            # Stop on first failure to avoid tight-looping on outage.
            break

    return {
        "attempted": attempted,
        "synced": synced,
        "pending": offline_store.sync_queue_length(),
    }


def start_sync_worker(sync_fn: Callable[[dict], bool]):
    global _worker_started

    if not Config.ENABLE_BACKGROUND_SYNC:
        logger.info("[SyncWorker] Disabled by config")
        return

    if not offline_store.is_available():
        logger.warning("[SyncWorker] Redis unavailable, worker not started")
        return

    with _worker_lock:
        if _worker_started:
            return

        def _run():
            logger.info(
                "[SyncWorker] Started (interval=%ss, batch=%s)",
                Config.SYNC_INTERVAL_SECONDS,
                Config.SYNC_BATCH_SIZE,
            )
            while True:
                try:
                    result = process_sync_queue(sync_fn, Config.SYNC_BATCH_SIZE)
                    if result["synced"] > 0:
                        logger.info(
                            "[SyncWorker] Synced=%s pending=%s",
                            result["synced"],
                            result["pending"],
                        )
                except Exception as exc:
                    logger.warning("[SyncWorker] Cycle failed: %s", exc)

                time.sleep(max(0.5, Config.SYNC_INTERVAL_SECONDS))

        thread = threading.Thread(target=_run, name="redis-sync-worker", daemon=True)
        thread.start()
        _worker_started = True
