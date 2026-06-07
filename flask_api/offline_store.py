"""
Redis-backed local cache + durable offline sync queue.

Design:
- Readings and alerts are always written locally first.
- Failed cloud writes are queued and retried by a background worker.
- If Redis is unavailable, callers can fall back to in-memory `data_store`.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from config import Config

logger = logging.getLogger(__name__)


class OfflineStore:
    def __init__(self):
        self._redis = None
        self._connect()

    def _connect(self):
        try:
            from redis import Redis

            if Config.REDIS_URL:
                self._redis = Redis.from_url(Config.REDIS_URL, decode_responses=True)
            else:
                self._redis = Redis(
                    host=Config.REDIS_HOST,
                    port=Config.REDIS_PORT,
                    db=Config.REDIS_DB,
                    password=Config.REDIS_PASSWORD or None,
                    ssl=Config.REDIS_SSL,
                    decode_responses=True,
                )

            self._redis.ping()
            logger.info("[Redis] Connected to local cache/queue")
        except Exception as exc:
            self._redis = None
            logger.warning("[Redis] Unavailable, falling back to in-memory only: %s", exc)

    def is_available(self) -> bool:
        return self._redis is not None

    def _loads(self, raw: str | None) -> dict | None:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _parse_iso(self, ts: str | None):
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None

    def cache_reading(self, payload: dict) -> bool:
        if not self._redis:
            return False
        try:
            raw = json.dumps(payload, separators=(",", ":"))
            with self._redis.pipeline() as pipe:
                pipe.rpush(Config.REDIS_KEY_READINGS, raw)
                pipe.ltrim(Config.REDIS_KEY_READINGS, -Config.MAX_RECORDS, -1)
                pipe.execute()
            return True
        except Exception as exc:
            logger.warning("[Redis] Failed to cache reading: %s", exc)
            return False

    def cache_alert(self, payload: dict) -> bool:
        if not self._redis:
            return False
        try:
            raw = json.dumps(payload, separators=(",", ":"))
            with self._redis.pipeline() as pipe:
                pipe.rpush(Config.REDIS_KEY_ALERTS, raw)
                pipe.ltrim(Config.REDIS_KEY_ALERTS, -Config.ALERTS_MAX_RECORDS, -1)
                pipe.execute()
            return True
        except Exception as exc:
            logger.warning("[Redis] Failed to cache alert: %s", exc)
            return False

    def get_latest_reading(self) -> dict | None:
        if not self._redis:
            return None
        try:
            return self._loads(self._redis.lindex(Config.REDIS_KEY_READINGS, -1))
        except Exception:
            return None

    def get_recent_readings(self, limit: int = 100) -> list[dict]:
        if not self._redis:
            return []
        limit = max(1, limit)
        try:
            rows = self._redis.lrange(Config.REDIS_KEY_READINGS, -limit, -1)
            parsed = [self._loads(r) for r in rows]
            return [p for p in parsed if p]
        except Exception:
            return []

    def get_readings_by_node(self, node_id: str, limit: int = 100) -> list[dict]:
        rows = self.get_recent_readings(limit=Config.MAX_RECORDS)
        matches = [r for r in rows if r.get("node_id") == node_id]
        return matches[-max(1, limit):]

    def get_readings_by_range(self, from_ts: str, to_ts: str, limit: int = 5000) -> list[dict]:
        from_dt = self._parse_iso(from_ts)
        to_dt = self._parse_iso(to_ts)
        if from_dt is None or to_dt is None:
            return []

        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=timezone.utc)
        if to_dt.tzinfo is None:
            to_dt = to_dt.replace(tzinfo=timezone.utc)

        rows = self.get_recent_readings(limit=Config.MAX_RECORDS)
        out: list[dict[str, Any]] = []
        for item in rows:
            ts = self._parse_iso(item.get("received_at"))
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if from_dt <= ts <= to_dt:
                out.append(item)
            if len(out) >= limit:
                break
        return out

    def get_alerts(self, limit: int = 100) -> list[dict]:
        if not self._redis:
            return []
        limit = max(1, limit)
        try:
            rows = self._redis.lrange(Config.REDIS_KEY_ALERTS, -limit, -1)
            parsed = [self._loads(r) for r in rows]
            return [p for p in parsed if p]
        except Exception:
            return []

    def get_latest_alert(self) -> dict | None:
        if not self._redis:
            return None
        try:
            return self._loads(self._redis.lindex(Config.REDIS_KEY_ALERTS, -1))
        except Exception:
            return None

    def enqueue_sync_reading(self, payload: dict) -> bool:
        if not self._redis:
            return False
        try:
            self._redis.rpush(Config.REDIS_KEY_SYNC_QUEUE, json.dumps(payload, separators=(",", ":")))
            return True
        except Exception as exc:
            logger.warning("[Redis] Failed to enqueue sync item: %s", exc)
            return False

    def peek_sync_reading(self) -> dict | None:
        if not self._redis:
            return None
        try:
            return self._loads(self._redis.lindex(Config.REDIS_KEY_SYNC_QUEUE, 0))
        except Exception:
            return None

    def pop_sync_reading(self) -> bool:
        if not self._redis:
            return False
        try:
            self._redis.lpop(Config.REDIS_KEY_SYNC_QUEUE)
            return True
        except Exception:
            return False

    def sync_queue_length(self) -> int:
        if not self._redis:
            return 0
        try:
            return int(self._redis.llen(Config.REDIS_KEY_SYNC_QUEUE))
        except Exception:
            return 0


offline_store = OfflineStore()
