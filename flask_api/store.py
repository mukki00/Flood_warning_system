"""
Thread-safe in-memory data store for sensor readings and alerts.
Keeps the last MAX_RECORDS entries using a deque.
"""

from collections import deque
from threading import Lock
from config import Config


class DataStore:
    def __init__(self):
        self._readings = deque(maxlen=Config.MAX_RECORDS)
        self._alerts   = deque(maxlen=100)
        self._lock     = Lock()

    # ── Readings ──────────────────────────────────────────────────────────

    def add_reading(self, payload: dict):
        with self._lock:
            self._readings.append(payload)

    def get_latest(self) -> dict | None:
        with self._lock:
            return self._readings[-1] if self._readings else None

    def get_all(self) -> list:
        with self._lock:
            return list(self._readings)

    def get_by_node(self, node_id: str) -> list:
        with self._lock:
            return [r for r in self._readings if r.get("node_id") == node_id]

    # ── Alerts ────────────────────────────────────────────────────────────

    def add_alert(self, payload: dict):
        with self._lock:
            self._alerts.append(payload)

    def get_alerts(self) -> list:
        with self._lock:
            return list(self._alerts)

    def get_latest_alert(self) -> dict | None:
        with self._lock:
            return self._alerts[-1] if self._alerts else None

    # ── Stats ─────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        with self._lock:
            latest = self._readings[-1] if self._readings else None
            return {
                "total_readings": len(self._readings),
                "total_alerts":   len(self._alerts),
                "latest_reading": latest,
                "latest_alert":   self._alerts[-1] if self._alerts else None,
            }


# Singleton shared across app and mqtt_client
data_store = DataStore()
