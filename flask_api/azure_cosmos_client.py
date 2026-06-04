"""
Azure Cosmos DB client — persists sensor readings as time-series documents.

Each reading is stored as a JSON document:
{
  "id":               "<node_id>-<timestamp_ms>",   ← unique Cosmos document ID
  "node_id":          "flood_node_1",
  "water_level_cm":   12.5,
  "rain_raw":         3100,
  "soil_moisture_raw":3200,
  "temperature_c":    27.5,
  "humidity_pct":     66.0,
  "risk_level":       "HIGH",
  "received_at":      "2026-06-03T07:00:00+00:00",
  "source":           "http" | "mqtt",
  "timestamp_ms":     1234567890
}
"""

import logging
from config import Config

logger = logging.getLogger(__name__)

# Cosmos SDK is optional — gracefully disabled if not installed or not configured
_cosmos_client = None
_container     = None


def _init_cosmos():
    global _cosmos_client, _container

    if not Config.COSMOS_ENDPOINT or not Config.COSMOS_KEY:
        logger.warning("[Cosmos] COSMOS_ENDPOINT or COSMOS_KEY not set — Azure persistence disabled.")
        return

    try:
        from azure.cosmos import CosmosClient, PartitionKey, exceptions

        _cosmos_client = CosmosClient(Config.COSMOS_ENDPOINT, credential=Config.COSMOS_KEY)

        # Create database if it doesn't exist
        db = _cosmos_client.create_database_if_not_exists(id=Config.COSMOS_DATABASE)

        # Create container if it doesn't exist; partition by node_id for efficient queries
        _container = db.create_container_if_not_exists(
            id=Config.COSMOS_CONTAINER,
            partition_key=PartitionKey(path="/node_id"),
            offer_throughput=400,  # minimum RU/s (free-tier friendly)
        )
        logger.info("[Cosmos] Connected to database='%s' container='%s'",
                    Config.COSMOS_DATABASE, Config.COSMOS_CONTAINER)

    except ImportError:
        logger.warning("[Cosmos] azure-cosmos package not installed — Azure persistence disabled.")
    except Exception as exc:
        logger.error("[Cosmos] Initialisation failed: %s", exc)


def save_reading(payload: dict) -> bool:
    """
    Persist a sensor reading to Cosmos DB.
    Returns True on success, False if disabled or on error.
    """
    if _container is None:
        return False

    try:
        # Build a unique document ID from node + timestamp
        node_id      = payload.get("node_id", "unknown")
        timestamp_ms = payload.get("timestamp_ms", 0)
        doc = {**payload, "id": f"{node_id}-{timestamp_ms}"}

        _container.upsert_item(doc)
        logger.debug("[Cosmos] Saved reading id=%s", doc["id"])
        return True

    except Exception as exc:
        logger.error("[Cosmos] Failed to save reading: %s", exc)
        return False


def query_latest(node_id: str, limit: int = 10) -> list:
    """
    Query the last `limit` readings for a given node from Cosmos DB.
    Returns a list of documents ordered by received_at descending.
    """
    if _container is None:
        return []

    try:
        query = (
            "SELECT TOP @limit * FROM c WHERE c.node_id = @node_id "
            "ORDER BY c.received_at DESC"
        )
        params = [
            {"name": "@limit",   "value": limit},
            {"name": "@node_id", "value": node_id},
        ]
        items = list(_container.query_items(query=query, parameters=params,
                                            enable_cross_partition_query=False))
        return items
    except Exception as exc:
        logger.error("[Cosmos] Query failed: %s", exc)
        return []


def query_readings_by_range(from_ts: str, to_ts: str, limit: int = 2000) -> list:
    """
    Query readings between two ISO-8601 timestamps (inclusive) from Cosmos DB.
    `from_ts` and `to_ts` are ISO strings, e.g. '2026-05-28T00:00:00+00:00'.
    Returns documents ordered by received_at ascending.
    """
    if _container is None:
        return []

    try:
        query = (
            "SELECT TOP @limit * FROM c "
            "WHERE c.received_at >= @from_ts AND c.received_at <= @to_ts "
            "ORDER BY c.received_at ASC"
        )
        params = [
            {"name": "@limit",   "value": limit},
            {"name": "@from_ts", "value": from_ts},
            {"name": "@to_ts",   "value": to_ts},
        ]
        items = list(_container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        ))
        return items
    except Exception as exc:
        logger.error("[Cosmos] Range query failed: %s", exc)
        return []


# Initialise on import
_init_cosmos()
