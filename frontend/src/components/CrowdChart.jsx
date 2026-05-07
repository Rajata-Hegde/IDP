import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export const CrowdChart = ({ history = [] }) => {
  if (history.length === 0) {
    return (
      <div className="flex h-64 w-full items-center justify-center rounded-[2rem] border border-white/10 bg-slate-950/70">
        <p className="text-sm text-slate-400">Waiting for crowd history...</p>
      </div>
    )
  }

  const data = history.map((count, idx) => ({
    time: idx,
    count: count
  }))

  return (
    <div className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-4 shadow-2xl shadow-black/20">
      <h3 className="mb-4 text-base font-semibold text-white">Crowd size history</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="time" stroke="#9ca3af" />
          <YAxis stroke="#9ca3af" />
          <Tooltip 
            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)' }}
            labelStyle={{ color: '#fff' }}
          />
          <Line 
            type="monotone" 
            dataKey="count" 
            stroke="#22d3ee" 
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
