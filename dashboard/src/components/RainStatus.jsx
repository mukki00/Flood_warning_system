import React from 'react'
import styles from './RainStatus.module.css'

/**
 * Displays rain sensor raw ADC value as a categorical indicator.
 * ESP32 ADC 0–4095. Higher raw value = drier (capacitive sensor).
 * Typical thresholds:
 *   > 3000 → No rain
 *   1500–3000 → Light rain
 *   < 1500 → Heavy rain
 */
export default function RainStatus({ rainRaw }) {
  const val = Number(rainRaw)

  let category, color, bars
  if (isNaN(val)) {
    category = 'Unknown'; color = '#8b949e'; bars = 0
  } else if (val > 3000) {
    category = 'No Rain';    color = '#3fb950'; bars = 1
  } else if (val > 1500) {
    category = 'Light Rain'; color = '#d29922'; bars = 2
  } else {
    category = 'Heavy Rain'; color = '#f85149'; bars = 3
  }

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
             stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="16" y1="13" x2="16" y2="21"/>
          <line x1="8"  y1="13" x2="8"  y2="21"/>
          <line x1="12" y1="15" x2="12" y2="23"/>
          <path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"/>
        </svg>
        <span className={styles.label}>Rain Sensor</span>
      </div>

      <div className={styles.valueRow}>
        <span className={styles.value}>{isNaN(val) ? '—' : val}</span>
        <span className={styles.unit}>ADC</span>
      </div>

      <div className={styles.categoryRow} style={{ color }}>
        <div className={styles.barsWrapper}>
          {[1, 2, 3].map((b) => (
            <div
              key={b}
              className={styles.bar}
              style={{
                height: `${b * 10 + 6}px`,
                background: b <= bars ? color : 'var(--border)',
              }}
            />
          ))}
        </div>
        <span className={styles.category}>{category}</span>
      </div>
    </div>
  )
}
