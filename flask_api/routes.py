"""
Flask API routes for the Flood Early Warning System.

Endpoints:
  POST /api/sensor-data          ← ESP32 HTTP POST (direct)
  GET  /api/sensor-data          ← All stored readings
  GET  /api/sensor-data/latest   ← Most recent reading
  GET  /api/sensor-data/<node>   ← Readings for a specific node
  GET  /api/alerts               ← All alerts
  GET  /api/alerts/latest        ← Most recent alert
  GET  /api/status               ← System health / summary
"""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from store import data_store
from azure_cosmos_client import save_reading, query_readings_by_range
from azure_eventhub_client import send_event

api = Blueprint("api", __name__, url_prefix="/api")


# ── Helpers ───────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {"node_id", "water_level_cm", "rain_raw",
                   "soil_moisture_raw", "temperature_c",
                   "humidity_pct", "risk_level"}


def _validate_payload(data: dict) -> str | None:
    """Return an error message string if invalid, else None."""
    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        return f"Missing required fields: {sorted(missing)}"

    try:
        wl = float(data["water_level_cm"])
        if wl < 0:
            return "water_level_cm must be >= 0"
    except (ValueError, TypeError):
        return "water_level_cm must be a number"

    if data["risk_level"] not in ("LOW", "MODERATE", "HIGH"):
        return "risk_level must be LOW, MODERATE or HIGH"

    return None


# ── Ingest (from ESP32 HTTP POST) ─────────────────────────────────────────────

@api.route("/sensor-data", methods=["POST"])
def ingest_sensor_data():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    error = _validate_payload(data)
    if error:
        return jsonify({"error": error}), 422

    data["received_at"] = datetime.now(timezone.utc).isoformat()
    data["source"] = "http"

    data_store.add_reading(data)

    # ── Persist to Azure Cosmos DB ──
    save_reading(data)

    # ── Forward to Azure Event Hub → Stream Analytics ──
    send_event(data)

    # Auto-generate an alert record for HIGH/MODERATE risk
    if data["risk_level"] in ("HIGH", "MODERATE"):
        alert = {
            "alert":       f"FLOOD_{data['risk_level']}",
            "node_id":     data["node_id"],
            "received_at": data["received_at"],
            "source":      "http",
        }
        data_store.add_alert(alert)

    return jsonify({"status": "ok", "received_at": data["received_at"]}), 201


# ── Query readings ─────────────────────────────────────────────────────────────

@api.route("/sensor-data", methods=["GET"])
def get_all_readings():
    from_ts = request.args.get("from")
    to_ts   = request.args.get("to")
    limit   = request.args.get("limit", default=100, type=int)

    # Date-range query → fetch from Cosmos DB
    if from_ts:
        if not to_ts:
            to_ts = datetime.now(timezone.utc).isoformat()
        readings = query_readings_by_range(from_ts, to_ts, limit=min(limit, 5000))
        if readings:
            return jsonify({"count": len(readings), "readings": readings,
                            "source": "cosmos", "from": from_ts, "to": to_ts}), 200
        # Fall back to in-memory if Cosmos is not configured
        readings = data_store.get_all()
        from_dt  = _parse_iso(from_ts)
        to_dt    = _parse_iso(to_ts)
        if from_dt:
            readings = [r for r in readings if _reading_in_range(r, from_dt, to_dt)]
        return jsonify({"count": len(readings), "readings": readings,
                        "source": "memory", "from": from_ts, "to": to_ts}), 200

    # Default: return last N from in-memory store
    readings = data_store.get_all()[-limit:]
    return jsonify({"count": len(readings), "readings": readings}), 200


def _parse_iso(ts: str):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _reading_in_range(reading: dict, from_dt, to_dt) -> bool:
    ts = _parse_iso(reading.get("received_at", ""))
    if ts is None:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return from_dt <= ts <= to_dt


@api.route("/sensor-data/latest", methods=["GET"])
def get_latest_reading():
    latest = data_store.get_latest()
    if latest is None:
        return jsonify({"error": "No data received yet"}), 404
    return jsonify(latest), 200


@api.route("/sensor-data/<string:node_id>", methods=["GET"])
def get_readings_by_node(node_id: str):
    readings = data_store.get_by_node(node_id)
    if not readings:
        return jsonify({"error": f"No data for node '{node_id}'"}), 404
    limit = request.args.get("limit", default=100, type=int)
    return jsonify({"node_id": node_id,
                    "count": len(readings[-limit:]),
                    "readings": readings[-limit:]}), 200


# ── Alerts ─────────────────────────────────────────────────────────────────────

@api.route("/alerts", methods=["GET"])
def get_alerts():
    alerts = data_store.get_alerts()
    return jsonify({"count": len(alerts), "alerts": alerts}), 200


@api.route("/alerts/latest", methods=["GET"])
def get_latest_alert():
    alert = data_store.get_latest_alert()
    if alert is None:
        return jsonify({"error": "No alerts yet"}), 404
    return jsonify(alert), 200


# ── System status ──────────────────────────────────────────────────────────────

@api.route("/status", methods=["GET"])
def get_status():
    summary = data_store.summary()
    summary["server_time"] = datetime.now(timezone.utc).isoformat()
    summary["status"] = "ok"
    return jsonify(summary), 200
