import { useState, useEffect, useCallback, useRef } from 'react'

const API_BASE = '/api'

// ── Time filter definitions ────────────────────────────────────────────────
export const TIME_FILTERS = [
  { key: 'live',    label: 'Live',    limit: 30,   intervalMs:  5_000, offsetMs: null },
  { key: '1h',      label: '1 Hour',  limit: 500,  intervalMs: 30_000, offsetMs:       60 * 60 * 1000 },
  { key: '24h',     label: '24 Hours',limit: 1000, intervalMs: 60_000, offsetMs:  24 * 60 * 60 * 1000 },
  { key: '7d',      label: '7 Days',  limit: 2000, intervalMs: 300_000, offsetMs:  7 * 24 * 60 * 60 * 1000 },
  { key: '30d',     label: '30 Days', limit: 2000, intervalMs: 300_000, offsetMs: 30 * 24 * 60 * 60 * 1000 },
  { key: '1y',      label: '1 Year',  limit: 2000, intervalMs: 300_000, offsetMs: 365 * 24 * 60 * 60 * 1000 },
]

export function useSensorData(filterKey = 'live') {
  const filter = TIME_FILTERS.find((f) => f.key === filterKey) || TIME_FILTERS[0]

  const [latest, setLatest]       = useState(null)
  const [history, setHistory]     = useState([])
  const [alerts, setAlerts]       = useState([])
  const [status, setStatus]       = useState(null)
  const [error, setError]         = useState(null)
  const [loading, setLoading]     = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const timerRef = useRef(null)

  const fetchAll = useCallback(async () => {
    try {
      // Build history URL – use date range for non-live filters
      let historyUrl
      if (filter.offsetMs) {
        const to   = new Date()
        const from = new Date(to.getTime() - filter.offsetMs)
        historyUrl = `${API_BASE}/sensor-data?from=${from.toISOString()}&to=${to.toISOString()}&limit=${filter.limit}`
      } else {
        historyUrl = `${API_BASE}/sensor-data?limit=${filter.limit}`
      }

      const [latestRes, historyRes, alertsRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/sensor-data/latest`),
        fetch(historyUrl),
        fetch(`${API_BASE}/alerts`),
        fetch(`${API_BASE}/status`),
      ])

      if (!latestRes.ok && latestRes.status !== 404) throw new Error(`Latest: ${latestRes.status}`)

      const [latestData, historyData, alertsData, statusData] = await Promise.all([
        latestRes.json(),
        historyRes.json(),
        alertsRes.json(),
        statusRes.json(),
      ])

      if (latestRes.ok && latestData) setLatest(latestData)
      if (historyData?.readings) setHistory(historyData.readings)
      if (alertsData?.alerts)    setAlerts(alertsData.alerts.slice(-10).reverse())
      if (statusData)            setStatus(statusData)

      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [filter.key]) // re-run whenever filter changes

  useEffect(() => {
    setLoading(true)
    setHistory([])
    fetchAll()
    timerRef.current = setInterval(fetchAll, filter.intervalMs)
    return () => clearInterval(timerRef.current)
  }, [fetchAll, filter.intervalMs])

  return { latest, history, alerts, status, error, loading, lastUpdated, refresh: fetchAll }
}

