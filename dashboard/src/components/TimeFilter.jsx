import React from 'react'
import { TIME_FILTERS } from '../hooks/useSensorData'
import styles from './TimeFilter.module.css'

export default function TimeFilter({ active, onChange }) {
  return (
    <div className={styles.wrapper}>
      <span className={styles.label}>Period:</span>
      <div className={styles.group}>
        {TIME_FILTERS.map((f) => (
          <button
            key={f.key}
            className={`${styles.btn} ${active === f.key ? styles.active : ''}`}
            onClick={() => onChange(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  )
}
