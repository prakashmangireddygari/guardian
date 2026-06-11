import { useState } from 'react'

const VIOLATION_TYPES = [
  '', 'sudden_braking', 'weaving', 'tailgating', 'amber_running', 'school_zone_speed'
]

export default function SearchPanel({ onSearch, onSelectPlate, api }) {
  const [plate, setPlate] = useState('')
  const [vtype, setVtype] = useState('')
  const [minScore, setMinScore] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [plateResults, setPlateResults] = useState([])

  const handleSearch = () => onSearch({ plate, violation_type: vtype, min_score: minScore, start_date: startDate, end_date: endDate })

  const searchPlate = async () => {
    if (plate.length < 2) return
    const res = await fetch(`${api}/police/search/plates?q=${plate}`)
    setPlateResults(await res.json())
  }

  return (
    <div className="bg-slate-800 rounded-xl p-4 space-y-3">
      <h2 className="font-semibold text-slate-300 text-sm uppercase tracking-wider">Search & Filter</h2>

      <div className="grid grid-cols-2 gap-3">
        <div className="relative">
          <input
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500"
            placeholder="Plate number..."
            value={plate}
            onChange={e => setPlate(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && searchPlate()}
          />
          {plateResults.length > 0 && (
            <div className="absolute z-10 mt-1 w-full bg-slate-700 rounded-lg shadow-lg">
              {plateResults.map(v => (
                <button key={v.plate}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-slate-600 flex justify-between"
                  onClick={() => { onSelectPlate(v.plate); setPlateResults([]) }}>
                  <span>{v.plate}</span>
                  <span className={`text-xs font-bold ${v.total_danger_score >= 50 ? 'text-red-400' : v.total_danger_score >= 25 ? 'text-orange-400' : 'text-green-400'}`}>
                    {v.total_danger_score}pts
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <select
          className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          value={vtype} onChange={e => setVtype(e.target.value)}>
          {VIOLATION_TYPES.map(t => (
            <option key={t} value={t}>{t || 'All violation types'}</option>
          ))}
        </select>

        <input type="number" placeholder="Min danger score" value={minScore}
          onChange={e => setMinScore(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm" />

        <div className="flex gap-2">
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
            className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-2 py-2 text-sm" />
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
            className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-2 py-2 text-sm" />
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={handleSearch}
          className="flex-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg py-2 text-sm font-semibold transition">
          Search Violations
        </button>
        <button onClick={searchPlate}
          className="flex-1 bg-slate-600 hover:bg-slate-500 text-white rounded-lg py-2 text-sm font-semibold transition">
          Find by Plate
        </button>
      </div>
    </div>
  )
}
