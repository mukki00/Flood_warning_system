"""
Configuration for the Flood Early Warning Flask API.
"""

import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on OS env vars

class Config:
    # ── Flask ──────────────────────────────────────────────────────────────
    HOST        = os.getenv("FLASK_HOST", "0.0.0.0")
    PORT        = int(os.getenv("FLASK_PORT", 5000))
    DEBUG       = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    SECRET_KEY  = os.getenv("FLASK_SECRET_KEY", "flood-warning-dev-key")

    # ── MQTT Broker ────────────────────────────────────────────────────────
    MQTT_BROKER        = os.getenv("MQTT_BROKER",       "broker.hivemq.com")
    MQTT_PORT          = int(os.getenv("MQTT_PORT",     "1883"))
    MQTT_TOPIC_DATA    = os.getenv("MQTT_TOPIC_DATA",   "flood/node1/data")
    MQTT_TOPIC_ALERTS  = os.getenv("MQTT_TOPIC_ALERTS", "flood/alerts/local")
    MQTT_CLIENT_ID     = os.getenv("MQTT_CLIENT_ID",    "FlaskFloodAPI")

    # ── In-memory storage limits ───────────────────────────────────────────
    MAX_RECORDS = int(os.getenv("MAX_RECORDS", "500"))  # keep last N readings

    # ── Azure Cosmos DB ────────────────────────────────────────────────────
    COSMOS_ENDPOINT   = os.getenv("COSMOS_ENDPOINT",   "")  # e.g. https://<account>.documents.azure.com:443/
    COSMOS_KEY        = os.getenv("COSMOS_KEY",        "")  # primary key
    COSMOS_DATABASE   = os.getenv("COSMOS_DATABASE",   "FloodWarningDB")
    COSMOS_CONTAINER  = os.getenv("COSMOS_CONTAINER",  "SensorReadings")

    # ── Azure Event Hub (feeds Stream Analytics) ───────────────────────────
    EVENTHUB_CONN_STR = os.getenv("EVENTHUB_CONN_STR", "")  # full connection string
    EVENTHUB_NAME     = os.getenv("EVENTHUB_NAME",     "flood-events")

    # ── Redis local-first cache / offline queue ───────────────────────────
    REDIS_URL         = os.getenv("REDIS_URL", "")
    REDIS_HOST        = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT        = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB          = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD    = os.getenv("REDIS_PASSWORD", "")
    REDIS_SSL         = os.getenv("REDIS_SSL", "false").lower() == "true"

    REDIS_KEY_READINGS   = os.getenv("REDIS_KEY_READINGS", "flood:readings")
    REDIS_KEY_ALERTS     = os.getenv("REDIS_KEY_ALERTS", "flood:alerts")
    REDIS_KEY_SYNC_QUEUE = os.getenv("REDIS_KEY_SYNC_QUEUE", "flood:sync:readings")
    ALERTS_MAX_RECORDS   = int(os.getenv("ALERTS_MAX_RECORDS", "200"))

    # ── Cloud sync controls (for hybrid/offline mode) ─────────────────────
    SYNC_TO_COSMOS        = os.getenv("SYNC_TO_COSMOS", "true").lower() == "true"
    SYNC_TO_EVENTHUB      = os.getenv("SYNC_TO_EVENTHUB", "true").lower() == "true"
    ENABLE_BACKGROUND_SYNC = os.getenv("ENABLE_BACKGROUND_SYNC", "true").lower() == "true"
    SYNC_BATCH_SIZE       = int(os.getenv("SYNC_BATCH_SIZE", "50"))
    SYNC_INTERVAL_SECONDS = float(os.getenv("SYNC_INTERVAL_SECONDS", "5"))
