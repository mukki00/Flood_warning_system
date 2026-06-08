# Flood Warning System

An IoT-enabled flood early warning platform with:
- ESP32 sensor simulation (Wokwi)
- Flask API for ingestion, local-first storage, and optional cloud sync
- React dashboard for live monitoring
- Redis cache and retry queue for offline resilience
- Optional Azure Cosmos DB and Azure Event Hub integration

## 1. Architecture at a Glance

```text
ESP32 (Wokwi)
  |- HTTP POST -> Flask API (/api/sensor-data)
  |- MQTT PUB  -> MQTT Broker

Flask API
  |- Stores readings locally first (memory + Redis)
  |- Tries immediate cloud sync (Cosmos/Event Hub)
  |- Queues failed cloud sync to Redis for retry worker

React Dashboard (Vite)
  |- Polls Flask API via /api/*
  |- Shows latest readings, history, alerts, and system status
```

## 2. Repository Structure

```text
/dashboard      React + Vite frontend (port 3000)
/flask_api      Flask backend API (port 5000)
/scripts        Local helper scripts (Redis startup, offline checks)
/wokwi          ESP32 simulation project
```

## 3. Prerequisites

Install these first:
- Git
- Node.js 18+ and npm
- Python 3.10+ (3.11 recommended)
- Docker Desktop (for Redis container)
- PowerShell (Windows; scripts are provided in `.ps1`)

Optional:
- Azure resources (Cosmos DB + Event Hub) for hybrid/cloud mode
- PlatformIO + Wokwi tooling for embedded simulation workflow

## 4. Quick Start (From Scratch)

## 4.1 Clone the repository

```bash
git clone https://github.com/mukki00/Flood_warning_system.git
cd Flood_warning_system
```

## 4.2 Backend setup (Flask API)

```bash
cd flask_api
python -m venv .venv
```

Activate virtual environment:

Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create local environment file:

Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

macOS/Linux:
```bash
cp .env.example .env
```

Edit `.env` based on your mode:
- Strict offline mode:
  - `SYNC_TO_COSMOS=false`
  - `SYNC_TO_EVENTHUB=false`
  - `ENABLE_BACKGROUND_SYNC=false`
- Hybrid mode (local + cloud):
  - Set valid Azure values and keep sync flags `true`

Return to project root:

```bash
cd ..
```

## 4.3 Start Redis (required)

Windows (PowerShell):

```powershell
./scripts/start-redis.ps1
```

If Docker is not running, start Docker Desktop and retry.

macOS/Linux (equivalent command):

```bash
docker run -d --name flood-redis -p 6379:6379 redis:7-alpine redis-server --appendonly yes --save 60 1000
```

## 4.4 Run Flask API

Windows (PowerShell):

```powershell
cd flask_api
.\.venv\Scripts\python.exe app.py
```

macOS/Linux:

```bash
cd flask_api
./.venv/bin/python app.py
```

API should be available at:
- `http://127.0.0.1:5000`

## 4.5 Run dashboard

Open a new terminal:

```bash
cd dashboard
npm install
npm run dev
```

Dashboard should be available at:
- `http://localhost:3000`

The Vite dev server proxies `/api` to `http://localhost:5000`.

## 5. Verify the full local flow

With Flask API and Redis running, use the included checker script from project root:

```powershell
./scripts/offline-check.ps1
```

It validates:
- API status endpoint
- sensor data POST
- latest reading retrieval
- alerts retrieval
- queue/storage/cloud target status

## 6. API Endpoints

Core endpoints:
- `POST /api/sensor-data`
- `GET /api/sensor-data`
- `GET /api/sensor-data/latest`
- `GET /api/sensor-data/{node_id}`
- `GET /api/alerts`
- `GET /api/alerts/latest`
- `GET /api/status`

Expected sensor payload fields:
- `node_id`
- `water_level_cm`
- `rain_raw`
- `soil_moisture_raw`
- `temperature_c`
- `humidity_pct`
- `risk_level` (`LOW`, `MODERATE`, `HIGH`)
- `timestamp_ms` (recommended)

## 7. Running Wokwi ESP32 Simulation (Optional)

1. Open the Wokwi project in `/wokwi`.
2. In `wokwi/src/main.cpp`, set `FLASK_API_URL` to your reachable Flask endpoint.
3. Start simulation and monitor serial output.
4. Confirm dashboard and `/api/status` update with incoming readings.

Notes:
- Default MQTT broker is public HiveMQ.
- For fully local/offline lab setups, point MQTT settings in Flask `.env` to a local broker.

## 8. Power BI Integration (Optional)

See detailed guide:
- `dashboard/POWERBI_GUIDE.md`

## 9. Troubleshooting

- Docker daemon error when starting Redis:
  - Start Docker Desktop, then rerun `./scripts/start-redis.ps1`.
- Dashboard cannot load API data:
  - Confirm Flask API is running on port 5000.
  - Confirm dashboard runs on port 3000.
- Redis unavailable in `/api/status`:
  - Verify container is running: `docker ps`.
  - Check Redis host/port in `flask_api/.env`.
- No cloud sync:
  - Confirm Azure credentials/settings in `.env`.
  - Check Flask logs for Cosmos/Event Hub initialization warnings.

## 10. Local Development Workflow

Recommended terminal layout:
- Terminal 1: Redis (`./scripts/start-redis.ps1`)
- Terminal 2: Flask API (`python app.py` from `/flask_api` venv)
- Terminal 3: Dashboard (`npm run dev` from `/dashboard`)
- Terminal 4 (optional): Offline verification (`./scripts/offline-check.ps1`)

## 11. Security Notes

- Do not commit real secrets in `.env`.
- Keep using `.env.example` as the template for teammates.
- Rotate Azure keys immediately if they were ever shared accidentally.

---

If you are onboarding a new teammate, the fastest path is:
1. Complete sections 4.1 to 4.5.
2. Run section 5 verification.
3. Use section 7 and section 8 only if your role includes IoT simulation or BI reporting.
