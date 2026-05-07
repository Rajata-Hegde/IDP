import React from 'react'

export const EventLog = ({ events = [] }) => {
  const displayEvents = events.slice().reverse().slice(0, 10)

  return (
    <div className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-4 shadow-2xl shadow-black/20">
      <h3 className="mb-4 text-base font-semibold text-white">Event log</h3>
      <div className="max-h-72 space-y-2 overflow-y-auto">
        {displayEvents.length === 0 ? (
          <p className="text-sm text-slate-400">No events logged yet.</p>
        ) : (
          displayEvents.map((event, idx) => (
            <div key={idx} className="rounded-2xl border border-white/10 bg-white/5 p-3 text-sm">
              <p className="text-[11px] text-slate-400">{new Date(event.timestamp).toLocaleTimeString()}</p>
              <p className="mt-1 font-medium text-white">{event.type}</p>
              <p className="mt-1 text-[11px] text-slate-300">
                Count: {event.data?.count ?? 0} · Avg: {(event.data?.average ?? 0).toFixed?.(1) ?? event.data?.average ?? 0} · Spike: {(event.data?.spike ?? 0).toFixed?.(1) ?? event.data?.spike ?? 0}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
