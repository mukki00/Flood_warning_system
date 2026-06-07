"""
MQTT subscriber — listens to HiveMQ broker and stores incoming
sensor payloads into the shared in-memory store.
"""

import json
import logging
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from config import Config
from store import data_store
from offline_store import offline_store
from cloud_sync import sync_reading_to_cloud

logger = logging.getLogger(__name__)


def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("[MQTT] Connected to broker %s:%d", Config.MQTT_BROKER, Config.MQTT_PORT)
        client.subscribe(Config.MQTT_TOPIC_DATA)
        client.subscribe(Config.MQTT_TOPIC_ALERTS)
        logger.info("[MQTT] Subscribed to: %s, %s",
                    Config.MQTT_TOPIC_DATA, Config.MQTT_TOPIC_ALERTS)
    else:
        logger.error("[MQTT] Connection failed with code %d", rc)


def _on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        payload["received_at"] = datetime.now(timezone.utc).isoformat()
        payload["source"] = "mqtt"

        if msg.topic == Config.MQTT_TOPIC_ALERTS:
            data_store.add_alert(payload)
            offline_store.cache_alert(payload)
            logger.info("[MQTT] Alert received: %s", payload)
        else:
            # Always store locally first.
            data_store.add_reading(payload)
            offline_store.cache_reading(payload)

            if not sync_reading_to_cloud(payload):
                offline_store.enqueue_sync_reading(payload)

            logger.info("[MQTT] Sensor data received from %s",
                        payload.get("node_id", "unknown"))
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("[MQTT] Failed to process message: %s", exc)


def _on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("[MQTT] Unexpected disconnect (rc=%d). Will auto-reconnect.", rc)


def start_mqtt_client():
    """Start the MQTT subscriber in a background daemon thread."""
    client = mqtt.Client(client_id=Config.MQTT_CLIENT_ID, clean_session=True)
    client.on_connect    = _on_connect
    client.on_message    = _on_message
    client.on_disconnect = _on_disconnect

    def _run():
        try:
            client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, keepalive=60)
            client.loop_forever()
        except Exception as exc:
            logger.error("[MQTT] Could not connect to broker: %s", exc)

    thread = threading.Thread(target=_run, name="mqtt-subscriber", daemon=True)
    thread.start()
    logger.info("[MQTT] Background subscriber thread started.")
    return client
