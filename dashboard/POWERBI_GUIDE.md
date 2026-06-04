# Power BI Dashboard — Flood Early Warning System

## Overview

This guide connects **Power BI Desktop** to the **Azure Cosmos DB** container
(`FloodWarningDB / SensorReadings`) populated by the MQTT → Flask pipeline,
and builds an interactive flood-monitoring dashboard.

---

## Prerequisites

| Tool | Version |
|---|---|
| Power BI Desktop | Latest (free download from microsoft.com/powerbi) |
| Azure Cosmos DB account | Already provisioned |
| Cosmos DB connector for PBI | Built-in (no extra install needed) |

---

## Step 1 — Connect Power BI to Azure Cosmos DB

1. Open **Power BI Desktop** → **Home** → **Get Data** → search **Azure Cosmos DB** → **Connect**.
2. Enter your Cosmos DB endpoint URL (from `.env` / `config.py`):  
   `https://<your-account>.documents.azure.com:443/`
3. Click **OK** → enter your **Primary Key** when prompted.
4. In the Navigator, expand **FloodWarningDB** → select **SensorReadings** → **Transform Data**.

---

## Step 2 — Transform the Data in Power Query

The Cosmos DB connector returns each document as a record inside a `Document` column.

In **Power Query Editor**:

```
1. Select the [Document] column → Home → Expand Column
2. Select the following fields to expand:
   - node_id
   - temperature_c
   - humidity_pct
   - water_level_cm
   - rain_raw
   - soil_moisture_raw
   - risk_level
   - received_at
   - source
3. Rename columns (Right-click → Rename):
   - temperature_c    → Temperature (°C)
   - humidity_pct     → Humidity (%)
   - water_level_cm   → Water Level (cm)
   - rain_raw         → Rain Raw (ADC)
   - risk_level       → Risk Level
   - received_at      → Timestamp
4. Change data types:
   - Temperature (°C)  → Decimal Number
   - Humidity (%)      → Decimal Number
   - Water Level (cm)  → Decimal Number
   - Rain Raw (ADC)    → Whole Number
   - Timestamp         → Date/Time (UTC)
5. Click Close & Apply
```

---

## Step 3 — Create Calculated Columns / Measures (DAX)

In the **Data** view, add these DAX measures:

### Latest Reading (per field)

```dax
Latest Temperature =
CALCULATE(
    LASTNONBLANK('SensorReadings'[Temperature (°C)], 1),
    ALL('SensorReadings')
)

Latest Humidity =
CALCULATE(
    LASTNONBLANK('SensorReadings'[Humidity (%)], 1),
    ALL('SensorReadings')
)

Latest Water Level =
CALCULATE(
    LASTNONBLANK('SensorReadings'[Water Level (cm)], 1),
    ALL('SensorReadings')
)

Latest Rain Raw =
CALCULATE(
    LASTNONBLANK('SensorReadings'[Rain Raw (ADC)], 1),
    ALL('SensorReadings')
)

Latest Risk Level =
CALCULATE(
    LASTNONBLANK('SensorReadings'[Risk Level], 1),
    ALL('SensorReadings')
)
```

### Risk Score (for conditional formatting / gauge)

```dax
Risk Score =
SWITCH(
    [Latest Risk Level],
    "LOW",      1,
    "MODERATE", 2,
    "HIGH",     3,
    0
)
```

### Rain Category (calculated column)

```dax
Rain Category =
SWITCH(
    TRUE(),
    'SensorReadings'[Rain Raw (ADC)] > 3000, "No Rain",
    'SensorReadings'[Rain Raw (ADC)] > 1500, "Light Rain",
    "Heavy Rain"
)
```

---

## Step 4 — Build the Dashboard Visuals

### Page 1 — Live Overview

| Visual | Type | Fields |
|---|---|---|
| Current Temperature | **Card** | `Latest Temperature` |
| Current Humidity | **Card** | `Latest Humidity` |
| Current Water Level | **Card** | `Latest Water Level` |
| Risk Level | **Card** | `Latest Risk Level` |
| Risk Gauge | **Gauge** | Value = `Risk Score`, Min=0, Max=3, Target=2 |
| Rain Status | **Card** | `Latest Rain Raw` |

**Conditional formatting on Risk Level card:**
- Rules: value contains "LOW" → green (#3fb950)  
- Rules: value contains "MODERATE" → amber (#d29922)  
- Rules: value contains "HIGH" → red (#f85149)

---

### Page 2 — Sensor Time Series

| Visual | Type | X-Axis | Y-Axis |
|---|---|---|---|
| Temperature over time | **Line chart** | Timestamp | Temperature (°C) |
| Humidity over time | **Line chart** | Timestamp | Humidity (%) |
| Water Level over time | **Area chart** | Timestamp | Water Level (cm) |
| Rain Sensor ADC | **Line chart** | Timestamp | Rain Raw (ADC) |

Add a **Date/Time slicer** (Timestamp field) at the top to filter time ranges.

---

### Page 3 — Alerts & Risk Distribution

| Visual | Type | Fields |
|---|---|---|
| Risk level distribution | **Donut chart** | Legend = Risk Level, Values = Count of node_id |
| Rain category breakdown | **Bar chart** | Axis = Rain Category, Values = Count |
| High-risk events table | **Table** | Timestamp, node_id, Water Level, Temperature, Risk Level — filtered to HIGH |
| Readings per hour | **Column chart** | X = Timestamp (Hour), Y = Count of rows |

---

## Step 5 — Auto-Refresh (Power BI Service)

1. **Publish** the report: **Home → Publish → My workspace**.
2. In **Power BI Service** → **Datasets** → select your dataset → **Schedule Refresh**:
   - Frequency: Every 30 minutes (or hourly)
   - Set your Azure Cosmos DB credentials in the **Data source credentials** panel.
3. Pin visuals to a **Dashboard** for a live tile view.

> **DirectQuery mode** (optional): In Power Query, use **Import mode** for historical analysis,
> or switch to **DirectQuery** if near-real-time refresh (< 1 min) is needed.
> DirectQuery requires a Power BI Premium capacity or Premium Per User licence.

---

## Step 6 — Row-Level Security (Optional)

If multiple sensor nodes exist, restrict users to specific nodes:

```dax
[node_id] = USERPRINCIPALNAME()
```

Apply via **Modelling → Manage Roles**.

---

## Colour Theme Reference

| Risk Level | Hex |
|---|---|
| LOW | `#3fb950` |
| MODERATE | `#d29922` |
| HIGH | `#f85149` |

Import the custom theme JSON below via **View → Themes → Browse for themes**:

```json
{
  "name": "FloodWarning",
  "dataColors": ["#58a6ff","#3fb950","#d29922","#f85149","#79c0ff","#bc8cff"],
  "background": "#0d1117",
  "foreground": "#e6edf3",
  "tableAccent": "#58a6ff"
}
```

---

## Architecture Summary

```
ESP32 (Wokwi)
    │ MQTT publish
    ▼
HiveMQ Broker
    │ subscribe
    ▼
Flask API (mqtt_client.py)
    │ save_reading()
    ▼
Azure Cosmos DB ◄──── Power BI DirectQuery / Scheduled Import
    │
    ▼
React Dashboard  (real-time polling /api/sensor-data/latest)
```
