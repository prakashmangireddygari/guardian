const BADGE = {
  sudden_braking: 'bg-yellow-900 text-yellow-300',
  weaving: 'bg-orange-900 text-orange-300',
  tailgating: 'bg-red-900 text-red-300',
  amber_running: 'bg-amber-900 text-amber-300',
  school_zone_speed: 'bg-purple-900 text-purple-300',
}

const fmt = (ts) => new Date(ts).toLocaleString()

export default function ViolationTable({ violations, total, onSelectPlate }) {
  if (!violations.length)
    return <div className="bg-slate-800 rounded-xl p-6 text-center text-slate-500 text-sm">No violations found. Use the search above.</div>

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700 flex justify-between items-center">
        <span className="font-semibold text-slate-300 text-sm">Violations</span>
        <span className="text-xs text-slate-500">{total} total</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-750">
            <tr className="text-slate-400 text-left">
              {['Plate', 'Type', 'Pts', 'Camera', 'Time'].map(h => (
                <th key={h} className="px-4 py-2 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {violations.map((v) => (
              <tr key={v.id} className="border-t border-slate-700 hover:bg-slate-700 transition">
                <td className="px-4 py-2">
                  <button className="text-blue-400 hover:underline font-mono"
                    onClick={() => onSelectPlate(v.plate)}>
                    {v.plate || '—'}
                  </button>
                </td>
                <td className="px-4 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${BADGE[v.violation_type] || 'bg-slate-700 text-slate-300'}`}>
                    {v.violation_type.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="px-4 py-2 font-bold text-red-400">+{v.danger_points}</td>
                <td className="px-4 py-2 text-slate-400">{v.camera_id}</td>
                <td className="px-4 py-2 text-slate-400">{fmt(v.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
