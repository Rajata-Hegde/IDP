import React from 'react'

export const StatusBanner = ({ status, count, average, riskLevel = 'LOW', density = 0, overcrowded = false, unusualGathering = false }) => {
  const isAlert = status === 'ALERT'
  const bgColor = isAlert ? 'bg-red-600/20 border-red-500' : 'bg-green-600/20 border-green-500'
  const textColor = isAlert ? 'text-red-400' : 'text-green-400'

  return (
    <div className={`border ${bgColor} rounded-2xl p-5`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className={`text-2xl font-semibold ${textColor} mb-2`}>
            {isAlert ? 'Crowd alert active' : 'Crowd conditions normal'}
          </h2>
          <p className="text-sm text-gray-300">
            Current count <span className="font-semibold text-white">{count}</span> ·
            Average <span className="font-semibold text-white">{average.toFixed(1)}</span>
          </p>
          <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-medium uppercase tracking-[0.18em]">
            <span className={`rounded-full border px-3 py-1 ${isAlert ? 'border-red-400/40 bg-red-500/10 text-red-100' : 'border-green-400/30 bg-green-500/10 text-green-100'}`}>
              Risk {riskLevel}
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-gray-200">
              Density {density}
            </span>
            <span className={`rounded-full border px-3 py-1 ${overcrowded ? 'border-amber-400/40 bg-amber-500/10 text-amber-100' : 'border-white/10 bg-white/5 text-gray-200'}`}>
              Overcrowding {overcrowded ? 'On' : 'Off'}
            </span>
            <span className={`rounded-full border px-3 py-1 ${unusualGathering ? 'border-fuchsia-400/40 bg-fuchsia-500/10 text-fuchsia-100' : 'border-white/10 bg-white/5 text-gray-200'}`}>
              Gathering {unusualGathering ? 'Detected' : 'Clear'}
            </span>
          </div>
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-full border ${isAlert ? 'border-red-400/40 bg-red-500/10 text-red-100' : 'border-green-400/40 bg-green-500/10 text-green-100'}`}>
          {isAlert ? '!' : '✓'}
        </div>
      </div>
    </div>
  )
}
