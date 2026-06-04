import React from 'react'
import styles from './SensorCard.module.css'

/**
 * Generic sensor metric card.
 * Props:
 *   icon       – React element
 *   label      – string, e.g. "Temperature"
 *   value      – number | string
 *   unit       – string, e.g. "°C"
 *   min/max    – numeric range for the fill bar
 *   color      – CSS colour for the accent bar
 *   subtext    – optional small label beneath the value
 */
export default function SensorCard({ icon, label, value, unit, min = 0, max = 100, color = '#58a6ff', subtext }) {
  const numVal   = parseFloat(value)
  const pct      = isNaN(numVal) ? 0 : Math.min(100, Math.max(0, ((numVal - min) / (max - min)) * 100))
  const display  = value === null || value === undefined ? '—' : value

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.icon} style={{ color }}>{icon}</span>
        <span className={styles.label}>{label}</span>
      </div>

      <div className={styles.valueRow}>
        <span className={styles.value}>{display}</span>
        {unit && <span className={styles.unit}>{unit}</span>}
      </div>

      {subtext && <div className={styles.subtext}>{subtext}</div>}

      {/* fill bar */}
      <div className={styles.barTrack}>
        <div className={styles.barFill} style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className={styles.rangeRow}>
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  )
}
