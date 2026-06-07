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
from azure_cosmos_client import query_readings_by_range
from offline_store import offline_store
from cloud_sync import sync_reading_to_cloud, active_targets

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

    # Always store locally first (in-memory + Redis cache)
    data_store.add_reading(data)
    offline_store.cache_reading(data)

    # Best-effort immediate cloud sync; queue for retry on failure
    cloud_synced = sync_reading_to_cloud(data)
    queued_for_sync = False
    if not cloud_synced:
        queued_for_sync = offline_store.enqueue_sync_reading(data)

    # Auto-generate an alert record for HIGH/MODERATE risk
    if data["risk_level"] in ("HIGH", "MODERATE"):
        alert = {
            "alert":       f"FLOOD_{data['risk_level']}",
            "node_id":     data["node_id"],
            "received_at": data["received_at"],
            "source":      "http",
        }
        data_store.add_alert(alert)
        offline_store.cache_alert(alert)

    return jsonify({
        "status": "ok",
        "received_at": data["received_at"],
        "cloud_synced": cloud_synced,
        "queued_for_sync": queued_for_sync,
    }), 201


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

        # Local-first: Redis cache → cloud → in-memory
        readings = offline_store.get_readings_by_range(from_ts, to_ts, limit=min(limit, 5000))
        if readings:
            return jsonify({"count": len(readings), "readings": readings,
                            "source": "redis", "from": from_ts, "to": to_ts}), 200

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
    readings = offline_store.get_recent_readings(limit=limit)
    if readings:
        return jsonify({"count": len(readings), "readings": readings, "source": "redis"}), 200

    readings = data_store.get_all()[-limit:]
    return jsonify({"count": len(readings), "readings": readings, "source": "memory"}), 200


def _parse_iso(ts: str):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
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
    latest = offline_store.get_latest_reading() or data_store.get_latest()
    if latest is None:
        return jsonify({"error": "No data received yet"}), 404
    return jsonify(latest), 200


@api.route("/sensor-data/<string:node_id>", methods=["GET"])
def get_readings_by_node(node_id: str):
    limit = request.args.get("limit", default=100, type=int)
    readings = offline_store.get_readings_by_node(node_id, limit=max(limit, 100))
    if not readings:
        readings = data_store.get_by_node(node_id)
    if not readings:
        return jsonify({"error": f"No data for node '{node_id}'"}), 404
    return jsonify({"node_id": node_id,
                    "count": len(readings[-limit:]),
                    "readings": readings[-limit:]}), 200


# ── Alerts ─────────────────────────────────────────────────────────────────────

@api.route("/alerts", methods=["GET"])
def get_alerts():
    alerts = offline_store.get_alerts(limit=200)
    source = "redis"
    if not alerts:
        alerts = data_store.get_alerts()
        source = "memory"
    return jsonify({"count": len(alerts), "alerts": alerts, "source": source}), 200


@api.route("/alerts/latest", methods=["GET"])
def get_latest_alert():
    alert = offline_store.get_latest_alert() or data_store.get_latest_alert()
    if alert is None:
        return jsonify({"error": "No alerts yet"}), 404
    return jsonify(alert), 200


# ── System status ──────────────────────────────────────────────────────────────

@api.route("/status", methods=["GET"])
def get_status():
    summary = data_store.summary()
    summary["server_time"] = datetime.now(timezone.utc).isoformat()
    summary["status"] = "ok"
    summary["storage"] = {
        "redis_available": offline_store.is_available(),
        "sync_queue_pending": offline_store.sync_queue_length(),
    }
    summary["cloud_targets"] = active_targets()

    # Derive current risk from the latest live reading (not from alerts).
    # latest_alert is a historical event; current_risk reflects the live sensor state.
    latest = offline_store.get_latest_reading() or data_store.get_latest()
    summary["current_risk"] = latest.get("risk_level", "UNKNOWN") if latest else "UNKNOWN"
    summary["alert_note"] = (
        "latest_alert shows the most recent triggered alert (historical). "
        "current_risk reflects the live sensor state."
    )

    return jsonify(summary), 200
