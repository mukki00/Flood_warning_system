import { useState, useEffect, useCallback, useRef } from 'react'

const API_BASE = '/api'
const POLL_INTERVAL_MS = 5000   // refresh every 5 s
const HISTORY_LIMIT    = 30     // keep last 30 readings for charts

export function useSensorData() {
  const [latest, setLatest]   = useState(null)
  const [history, setHistory] = useState([])
  const [alerts, setAlerts]   = useState([])
  const [status, setStatus]   = useState(null)
  const [error, setError]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const timerRef = useRef(null)

  const fetchAll = useCallback(async () => {
    try {
      const [latestRes, historyRes, alertsRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/sensor-data/latest`),
        fetch(`${API_BASE}/sensor-data?limit=${HISTORY_LIMIT}`),
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
  }, [])

  useEffect(() => {
    fetchAll()
    timerRef.current = setInterval(fetchAll, POLL_INTERVAL_MS)
    return () => clearInterval(timerRef.current)
  }, [fetchAll])

  return { latest, history, alerts, status, error, loading, lastUpdated, refresh: fetchAll }
}
