import { useEffect, useState } from 'react'

export default function VehicleDetail({ plate, api, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`${api}/police/vehicle/${plate}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [plate])

  const scoreColor = (s) => s >= 60 ? 'text-red-400' : s >= 25 ? 'text-orange-400' : 'text-green-400'
  const riskLabel = (s) => s >= 60 ? 'HIGH RISK' : s >= 25 ? 'MEDIUM RISK' : 'LOW RISK'

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      <div className="flex justify-between items-center px-4 py-3 border-b border-slate-700">
        <span className="font-mono font-bold text-blue-300 text-lg">{plate}</span>
        <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
      </div>

      {loading && <div className="p-6 text-center text-slate-400 text-sm">Loading...</div>}

      {data && !loading && (
        <div className="p-4 space-y-3">
          <div className="flex justify-between">
            <div>
              <p className="text-xs text-slate-400">Total Danger Score</p>
              <p className={`text-3xl font-black ${scoreColor(data.total_danger_score)}`}>
                {data.total_danger_score}
              </p>
            </div>
            <span className={`self-start text-xs font-bold px-2 py-1 rounded ${data.total_danger_score >= 60 ? 'bg-red-900 text-red-300' : data.total_danger_score >= 25 ? 'bg-orange-900 text-orange-300' : 'bg-green-900 text-green-300'}`}>
              {riskLabel(data.total_danger_score)}
            </span>
          </div>

          <div className="text-xs text-slate-400 space-y-0.5">
            <p>First seen: {new Date(data.first_seen).toLocaleString()}</p>
            <p>Last seen: {new Date(data.last_seen).toLocaleString()}</p>
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-400 mb-1 uppercase tracking-wide">Recent Violations</p>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {(data.violations || []).slice(0, 10).map(v => (
                <div key={v.id} className="flex justify-between text-xs bg-slate-700 rounded px-2 py-1">
                  <span className="text-slate-300">{v.violation_type.replace(/_/g, ' ')}</span>
                  <span className="text-red-400 font-bold">+{v.danger_points}</span>
                </div>
              ))}
              {!data.violations?.length && <p className="text-slate-500 text-xs">No violations recorded.</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
