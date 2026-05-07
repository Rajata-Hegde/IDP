import React from 'react'

export const MetricCard = ({ title, value, unit = '', color = 'blue', icon = '📊' }) => {
  const colorClasses = {
    blue: 'border-blue-500 bg-blue-500/10',
    green: 'border-green-500 bg-green-500/10',
    red: 'border-red-500 bg-red-500/10',
    yellow: 'border-yellow-500 bg-yellow-500/10',
  }

  return (
    <div className={`border ${colorClasses[color]} rounded-2xl p-4 backdrop-blur-sm hover:shadow-lg transition-shadow`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-gray-400 mb-2">{title}</p>
          <p className="text-2xl font-semibold text-white">
            {typeof value === 'number' ? value.toFixed(1) : value}
            {unit && <span className="text-sm ml-1 text-gray-400">{unit}</span>}
          </p>
        </div>
        <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-full bg-white/5 text-sm text-white/90">
          {typeof icon === 'string' ? icon : React.createElement(icon, { className: 'h-4 w-4' })}
        </div>
      </div>
    </div>
  )
}
