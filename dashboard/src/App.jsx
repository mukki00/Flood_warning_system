import React, { useState } from 'react'
import { useSensorData } from './hooks/useSensorData'
import SensorCard     from './components/SensorCard'
import RiskIndicator  from './components/RiskIndicator'
import SensorChart    from './components/SensorChart'
import AlertList      from './components/AlertList'
import RainStatus     from './components/RainStatus'
import TimeFilter     from './components/TimeFilter'
import styles         from './App.module.css'

// ── Inline SVG icons (no external dep) ───────────────────────────────────────
const ThermIcon = ({ color }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
       stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>
  </svg>
)
const HumidIcon = ({ color }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
       stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
  </svg>
)
const WaterIcon = ({ color }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
       stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
  </svg>
)
const RefreshIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10"/>
    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
)

function formatDate(d) {
  if (!d) return ''
  return d.toLocaleTimeString()
}

export default function App() {
  const [filterKey, setFilterKey] = useState('live')
  const { latest, history, alerts, status, error, loading, lastUpdated, refresh } = useSensorData(filterKey)

  const temp     = latest?.temperature_c   ?? null
  const humidity = latest?.humidity_pct    ?? null
  const water    = latest?.water_level_cm  ?? null
  const rain     = latest?.rain_raw        ?? null
  const risk     = latest?.risk_level      ?? 'LOW'
  const node     = latest?.node_id         ?? '—'

  // Determine temp colour based on value
  const tempColor = temp === null ? '#58a6ff'
    : temp > 35  ? '#f85149'
    : temp > 28  ? '#d29922'
    : '#58a6ff'

  // Determine water colour
  const waterColor = water === null ? '#58a6ff'
    : water > 80  ? '#f85149'
    : water > 50  ? '#d29922'
    : '#58a6ff'

  return (
    <div className={styles.root}>
      {/* ── Header ─────────────────────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.logo}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                 stroke="#58a6ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div>
            <h1 className={styles.title}>Flood Early Warning System</h1>
            <p className={styles.subtitle}>Real-time IoT Sensor Dashboard · Node: <strong>{node}</strong></p>
          </div>
        </div>
        <div className={styles.headerRight}>
          {error && <span className={styles.errorBadge}>⚠ {error}</span>}
          <span className={styles.updated}>
            {loading ? 'Fetching…' : lastUpdated ? `Updated ${formatDate(lastUpdated)}` : ''}
          </span>
          <button className={styles.refreshBtn} onClick={refresh} title="Refresh now">
            <RefreshIcon /> Refresh
          </button>
        </div>
      </header>

      <main className={styles.main}>
        {/* ── Risk Banner ─────────────────────────────────── */}
        <section className={styles.riskSection}>
          <RiskIndicator riskLevel={risk} />
          <div className={styles.statusCards}>
            <div className={styles.statCard}>
              <span className={styles.statLabel}>Total Readings</span>
              <span className={styles.statVal}>{status?.total_readings ?? '—'}</span>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statLabel}>Total Alerts</span>
              <span className={styles.statVal}>{status?.total_alerts ?? '—'}</span>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statLabel}>Poll Interval</span>
              <span className={styles.statVal}>5 s</span>
            </div>
          </div>
        </section>

        {/* ── Sensor Metric Cards ──────────────────────────── */}
        <section className={styles.metricsGrid}>
          <SensorCard
            icon={<ThermIcon color={tempColor} />}
            label="Temperature"
            value={temp !== null ? Number(temp).toFixed(1) : null}
            unit="°C"
            min={-10} max={60}
            color={tempColor}
            subtext={temp > 35 ? 'High — heat stress risk' : temp > 28 ? 'Elevated' : 'Normal range'}
          />
          <SensorCard
            icon={<HumidIcon color="#79c0ff" />}
            label="Humidity"
            value={humidity !== null ? Number(humidity).toFixed(1) : null}
            unit="%"
            min={0} max={100}
            color="#79c0ff"
            subtext={humidity > 80 ? 'Very High — saturation risk' : humidity > 60 ? 'Elevated' : 'Normal range'}
          />
          <SensorCard
            icon={<WaterIcon color={waterColor} />}
            label="Water Level"
            value={water !== null ? Number(water).toFixed(1) : null}
            unit="cm"
            min={0} max={150}
            color={waterColor}
            subtext={water > 80 ? 'Critical level!' : water > 50 ? 'Rising — monitor closely' : 'Safe level'}
          />
          <RainStatus rainRaw={rain} />
        </section>

        {/* ── Historical Charts ────────────────────────────── */}
        <section className={styles.chartsSection}>
          <div className={styles.chartsHeader}>
            <span className={styles.chartsTitle}>Historical Charts</span>
            <TimeFilter active={filterKey} onChange={setFilterKey} />
          </div>
          <div className={styles.chartsGrid}>
            <SensorChart
              title="Temperature History (°C)"
              data={history}
              dataKey="temperature_c"
              unit="°C"
              color={tempColor}
              filterKey={filterKey}
            />
            <SensorChart
              title="Humidity History (%)"
              data={history}
              dataKey="humidity_pct"
              unit="%"
              color="#79c0ff"
              filterKey={filterKey}
            />
            <SensorChart
              title="Water Level History (cm)"
              data={history}
              dataKey="water_level_cm"
              unit="cm"
              color={waterColor}
              filterKey={filterKey}
            />
            <SensorChart
              title="Rain Sensor (ADC Raw)"
              data={history}
              dataKey="rain_raw"
              unit=""
              color="#bc8cff"
              type="line"
              filterKey={filterKey}
            />
          </div>
        </section>

        {/* ── Alerts ──────────────────────────────────────── */}
        <section className={styles.alertsSection}>
          <AlertList alerts={alerts} />
        </section>
      </main>

      <footer className={styles.footer}>
        MSc CS7080NM · IoT Flood Early Warning System · Data via MQTT → Flask → Azure Cosmos DB
      </footer>
    </div>
  )
}
