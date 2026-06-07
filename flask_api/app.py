"""
Flood Early Warning System — Flask API entry point.

Starts:
  1. Flask HTTP server  (receives direct ESP32 POSTs)
  2. MQTT subscriber    (receives broker-forwarded messages)
"""

import logging
from flask import Flask
from flask_cors import CORS

from config import Config
from routes import api
from mqtt_client import start_mqtt_client
from cloud_sync import sync_reading_to_cloud
from sync_worker import start_sync_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = Config.SECRET_KEY

    # Allow cross-origin requests from the dashboard
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register API blueprint
    app.register_blueprint(api)

    return app


if __name__ == "__main__":
    app = create_app()

    # Start MQTT subscriber in background thread
    start_mqtt_client()

    # Start retry worker that drains Redis sync queue when cloud is reachable
    start_sync_worker(sync_reading_to_cloud)

    logger.info("Starting Flask API on %s:%d", Config.HOST, Config.PORT)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)
