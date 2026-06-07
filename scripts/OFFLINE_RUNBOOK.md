# Offline/Hybrid Local Runbook

## 1) Prepare backend config

1. Copy `flask_api/.env.example` to `flask_api/.env`.
2. Fill only what you need:
- For strict offline mode: leave `COSMOS_*` and `EVENTHUB_*` empty.
- For hybrid mode: keep Azure values and `SYNC_TO_COSMOS=true`, `SYNC_TO_EVENTHUB=true`.

## 2) Start Redis (required for cache + retry queue)

```powershell
Set-Location d:/MSc/25024576_CS7080NM_A2
./scripts/start-redis.ps1
```

If you get Docker daemon errors, start Docker Desktop first and retry.

## 3) Start Flask API

```powershell
Set-Location d:/MSc/25024576_CS7080NM_A2/flask_api
../.venv/Scripts/python.exe app.py
```

## 4) Run offline verification script

In another terminal:

```powershell
Set-Location d:/MSc/25024576_CS7080NM_A2
./scripts/offline-check.ps1
```

## 5) Expected outcomes

- `/api/status` shows `storage.redis_available=true`.
- Posting sensor data returns `status=ok`.
- During internet outage in hybrid mode, `sync_queue_pending` increases.
- After internet returns, `sync_queue_pending` decreases as worker drains queue.

## 6) Optional strict offline mode

Use these in `flask_api/.env`:

```dotenv
SYNC_TO_COSMOS=false
SYNC_TO_EVENTHUB=false
ENABLE_BACKGROUND_SYNC=false
```

This keeps all processing local.
