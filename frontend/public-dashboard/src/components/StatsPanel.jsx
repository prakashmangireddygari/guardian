const LABELS = {
  sudden_braking: 'Sudden Braking',
  weaving: 'Lane Weaving',
  tailgating: 'Tailgating',
  amber_running: 'Amber Running',
  school_zone_speed: 'School Zone Speed',
}

export default function StatsPanel({ stats }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-800 rounded-lg p-3">
          <p className="text-xs text-slate-400">Total Incidents</p>
          <p className="text-2xl font-black text-emerald-400">{stats.total_incidents_recorded}</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-3">
          <p className="text-xs text-slate-400">High Risk Zones</p>
          <p className="text-2xl font-black text-red-400">{stats.high_risk_zones}</p>
        </div>
      </div>

      <div className="bg-slate-800 rounded-lg p-3">
        <p className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wide">Incidents by Type</p>
        <div className="space-y-1.5">
          {(stats.by_violation_type || []).map(({ type, count }) => (
            <div key={type} className="flex justify-between text-xs">
              <span className="text-slate-300">{LABELS[type] || type}</span>
              <span className="font-bold text-slate-100">{count}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-slate-600 text-center">
        Data refreshes every 30 seconds. No identifying information is shown.
      </p>
    </div>
  )
}
