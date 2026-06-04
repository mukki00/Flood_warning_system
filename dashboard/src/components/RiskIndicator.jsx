import React from 'react'
import styles from './RiskIndicator.module.css'

const LEVELS = ['LOW', 'MODERATE', 'HIGH']

const META = {
  LOW:      { color: '#3fb950', bg: 'rgba(63,185,80,0.12)',  label: 'LOW RISK',      desc: 'Normal conditions. No immediate flood threat.' },
  MODERATE: { color: '#d29922', bg: 'rgba(210,153,34,0.12)', label: 'MODERATE RISK', desc: 'Elevated readings. Monitor closely.' },
  HIGH:     { color: '#f85149', bg: 'rgba(248,81,73,0.12)',  label: 'HIGH RISK',     desc: 'FLOOD WARNING! Immediate action required.' },
}

export default function RiskIndicator({ riskLevel }) {
  const level = (riskLevel || 'LOW').toUpperCase()
  const meta  = META[level] || META.LOW

  return (
    <div className={styles.wrapper} style={{ borderColor: meta.color, background: meta.bg }}>
      <div className={styles.levelRow}>
        {LEVELS.map((l) => {
          const m       = META[l]
          const active  = l === level
          const reached = LEVELS.indexOf(l) <= LEVELS.indexOf(level)
          return (
            <div
              key={l}
              className={`${styles.pill} ${active ? styles.active : ''}`}
              style={reached ? { background: m.color, borderColor: m.color } : {}}
            >
              {l}
            </div>
          )
        })}
      </div>

      {/* pulsing indicator */}
      <div className={styles.statusRow}>
        <span
          className={`${styles.dot} ${level === 'HIGH' ? styles.pulse : ''}`}
          style={{ background: meta.color }}
        />
        <span className={styles.label} style={{ color: meta.color }}>
          {meta.label}
        </span>
      </div>

      <p className={styles.desc}>{meta.desc}</p>
    </div>
  )
}
