export default function StatsBar({ stats }) {
  const cards = [
    { label: 'Total Vehicles', value: stats.total_vehicles, color: 'text-blue-400' },
    { label: 'Total Violations', value: stats.total_violations, color: 'text-yellow-400' },
    { label: 'High Risk Vehicles', value: stats.high_risk_vehicles, color: 'text-red-400' },
  ]
  return (
    <div className="grid grid-cols-3 gap-3">
      {cards.map(c => (
        <div key={c.label} className="bg-slate-800 rounded-xl px-4 py-3">
          <p className="text-xs text-slate-400">{c.label}</p>
          <p className={`text-2xl font-black ${c.color}`}>{c.value ?? '—'}</p>
        </div>
      ))}
    </div>
  )
}
