"""
Azure Event Hub producer — forwards sensor events to Azure Stream Analytics.

Stream Analytics reads from this Event Hub, evaluates flood risk rules,
and triggers Logic Apps (Email / SMS / Push) when thresholds are exceeded.
"""

import json
import logging
from config import Config

logger = logging.getLogger(__name__)

_producer = None


def _init_eventhub():
    global _producer

    if not Config.EVENTHUB_CONN_STR:
        logger.warning("[EventHub] EVENTHUB_CONN_STR not set — Event Hub streaming disabled.")
        return

    try:
        from azure.eventhub import EventHubProducerClient

        _producer = EventHubProducerClient.from_connection_string(
            conn_str=Config.EVENTHUB_CONN_STR,
            eventhub_name=Config.EVENTHUB_NAME,
        )
        logger.info("[EventHub] Producer ready for hub='%s'", Config.EVENTHUB_NAME)

    except ImportError:
        logger.warning("[EventHub] azure-eventhub package not installed — streaming disabled.")
    except Exception as exc:
        logger.error("[EventHub] Initialisation failed: %s", exc)


def send_event(payload: dict) -> bool:
    """
    Send a single sensor reading as an Event Hub event.
    Returns True on success, False if disabled or on error.
    """
    if _producer is None:
        return False

    try:
        from azure.eventhub import EventData

        with _producer:
            batch = _producer.create_batch()
            batch.add(EventData(json.dumps(payload)))
            _producer.send_batch(batch)

        logger.debug("[EventHub] Event sent for node=%s risk=%s",
                     payload.get("node_id"), payload.get("risk_level"))
        return True

    except Exception as exc:
        logger.error("[EventHub] Failed to send event: %s", exc)
        return False


# Initialise on import
_init_eventhub()
