import React from 'react'
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import styles from './SensorChart.module.css'

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`
}

const CustomTooltip = ({ active, payload, label, unit }) => {
  if (active && payload && payload.length) {
    return (
      <div className={styles.tooltip}>
        <p className={styles.tooltipTime}>{label}</p>
        <p className={styles.tooltipVal} style={{ color: payload[0].color }}>
          {payload[0].value?.toFixed(2)} {unit}
        </p>
      </div>
    )
  }
  return null
}

/**
 * Props:
 *   title   – chart heading
 *   data    – array of reading objects
 *   dataKey – field name in the reading objects
 *   unit    – display unit
 *   color   – stroke color
 *   type    – 'area' | 'line'  (default: 'area')
 */
export default function SensorChart({ title, data, dataKey, unit, color = '#58a6ff', type = 'area' }) {
  const chartData = data.map((r) => ({
    time:  formatTime(r.received_at),
    value: r[dataKey] !== undefined ? Number(r[dataKey]) : null,
  }))

  const ChartComp = type === 'line' ? LineChart : AreaChart

  return (
    <div className={styles.card}>
      <div className={styles.title}>{title}</div>
      <ResponsiveContainer width="100%" height={180}>
        <ChartComp data={chartData} margin={{ top: 4, right: 12, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#30363d" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="time"
            tick={{ fill: '#8b949e', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#8b949e', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip unit={unit} />} />
          {type === 'area'
            ? <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2}
                    fill={`url(#grad-${dataKey})`} dot={false} activeDot={{ r: 4 }} />
            : <Line  type="monotone" dataKey="value" stroke={color} strokeWidth={2}
                    dot={false} activeDot={{ r: 4 }} />
          }
        </ChartComp>
      </ResponsiveContainer>
    </div>
  )
}
