import React from 'react'
import styles from './AlertList.module.css'

const COLORS = {
  FLOOD_HIGH:     '#f85149',
  FLOOD_MODERATE: '#d29922',
}

function relativeTime(ts) {
  if (!ts) return ''
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
  if (diff < 60)  return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export default function AlertList({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className={styles.card}>
        <div className={styles.heading}>Recent Alerts</div>
        <p className={styles.empty}>No alerts generated yet.</p>
      </div>
    )
  }

  return (
    <div className={styles.card}>
      <div className={styles.heading}>Recent Alerts</div>
      <ul className={styles.list}>
        {alerts.map((a, i) => {
          const color = COLORS[a.alert] || '#8b949e'
          return (
            <li key={i} className={styles.item}>
              <span className={styles.dot} style={{ background: color }} />
              <div className={styles.info}>
                <span className={styles.alertType} style={{ color }}>{a.alert}</span>
                <span className={styles.node}>{a.node_id}</span>
              </div>
              <span className={styles.time}>{relativeTime(a.received_at)}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
