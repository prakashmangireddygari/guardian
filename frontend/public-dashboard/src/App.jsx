import { useEffect, useState } from 'react'
import HeatmapView from './components/HeatmapView'
import StatsPanel from './components/StatsPanel'

const API = 'http://localhost:8000'

export default function App() {
  const [zones, setZones] = useState([])
  const [stats, setStats] = useState(null)

  useEffect(() => {
    const load = async () => {
      const [heatRes, statsRes] = await Promise.all([
        fetch(`${API}/public/heatmap`),
        fetch(`${API}/public/stats`),
      ])
      const heatData = await heatRes.json()
      const statsData = await statsRes.json()
      setZones(heatData.zones || [])
      setStats(statsData)
    }
    load()
    const interval = setInterval(load, 30_000) // refresh every 30s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-xl font-bold text-emerald-400">🛡 Guardian — Public Safety Map</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Showing anonymised risk zones. No plates, no faces — just safety data.
        </p>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Map */}
        <div className="flex-1 relative">
          <HeatmapView zones={zones} />
        </div>

        {/* Sidebar */}
        <div className="w-72 p-4 border-l border-slate-700 overflow-y-auto">
          {stats && <StatsPanel stats={stats} />}
          <div className="mt-4 text-xs text-slate-500 space-y-1">
            <p className="font-semibold text-slate-400">Risk Level Guide</p>
            <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-green-500 inline-block"></span> Low risk zone</div>
            <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-yellow-500 inline-block"></span> Moderate risk</div>
            <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-500 inline-block"></span> High risk zone</div>
          </div>
        </div>
      </div>
    </div>
  )
}
