export default function AlertFeed({ alerts }) {
  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
        <span className="font-semibold text-slate-300 text-sm">Live Alerts</span>
      </div>
      <div className="max-h-72 overflow-y-auto divide-y divide-slate-700">
        {alerts.length === 0 && (
          <p className="text-center text-slate-500 text-xs py-6">No active alerts</p>
        )}
        {alerts.map((a, i) => (
          <div key={i} className={`px-4 py-2 text-xs ${a.level === 'CRITICAL' || a.level === 'DANGER' ? 'bg-red-950' : 'bg-orange-950'}`}>
            <div className="flex justify-between mb-0.5">
              <span className={`font-bold ${a.level === 'CRITICAL' || a.level === 'DANGER' ? 'text-red-400' : 'text-orange-400'}`}>
                {a.level} — {a.type?.toUpperCase()}
              </span>
              <span className="text-slate-500">{new Date(a.ts).toLocaleTimeString()}</span>
            </div>
            {a.distance_m !== undefined && <span className="text-slate-300">Distance: {a.distance_m}m</span>}
            {a.ttc_seconds !== undefined && <span className="text-slate-300">TTC: {a.ttc_seconds}s</span>}
            <div className="text-slate-500">Vehicles: {a.vehicle_ids?.join(', ')}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
