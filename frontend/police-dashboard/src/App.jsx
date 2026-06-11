import { useState, useEffect, useRef } from 'react'
import SearchPanel from './components/SearchPanel'
import ViolationTable from './components/ViolationTable'
import VehicleDetail from './components/VehicleDetail'
import AlertFeed from './components/AlertFeed'
import StatsBar from './components/StatsBar'

const API = 'http://localhost:8000'
const WS_URL = 'ws://localhost:8000/ws/alerts'

export default function App() {
  const [violations, setViolations] = useState([])
  const [total, setTotal] = useState(0)
  const [selectedPlate, setSelectedPlate] = useState(null)
  const [liveAlerts, setLiveAlerts] = useState([])
  const [stats, setStats] = useState(null)
  const [weather, setWeather] = useState(null)
  const wsRef = useRef(null)

  // Live WebSocket feed
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL)
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data)
        if (data.type === 'frame') {
          const critical = [
            ...data.distance_alerts.filter(a => a.level === 'DANGER'),
            ...data.collision_alerts.filter(a => a.level === 'CRITICAL'),
          ]
          if (critical.length > 0) {
            setLiveAlerts(prev => [...critical.map(a => ({ ...a, ts: Date.now() })), ...prev].slice(0, 50))
          }
          if (data.weather) setWeather(data.weather)
        }
      }
      ws.onclose = () => setTimeout(connect, 3000)
      wsRef.current = ws
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  const search = async (params) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))
    )
    const res = await fetch(`${API}/police/search/violations?${qs}`)
    const data = await res.json()
    setViolations(data.violations || [])
    setTotal(data.total || 0)
  }

  const loadStats = async () => {
    const res = await fetch(`${API}/police/stats/summary`)
    setStats(await res.json())
  }

  useEffect(() => { loadStats() }, [])

  return (
    <div className="min-h-screen p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-700 pb-3">
        <h1 className="text-2xl font-bold tracking-wide text-blue-400">
          🛡 GUARDIAN — Police Dashboard
        </h1>
        {weather && (
          <div className="text-sm bg-slate-800 px-3 py-1 rounded-full text-yellow-300">
            {weather.condition.toUpperCase()} | ×{weather.threshold_multiplier}
          </div>
        )}
      </div>

      {stats && <StatsBar stats={stats} />}

      <div className="grid grid-cols-12 gap-4">
        {/* Left: Search + Table */}
        <div className="col-span-8 space-y-4">
          <SearchPanel onSearch={search} onSelectPlate={setSelectedPlate} api={API} />
          <ViolationTable violations={violations} total={total} onSelectPlate={setSelectedPlate} />
        </div>

        {/* Right: Detail + Live alerts */}
        <div className="col-span-4 space-y-4">
          {selectedPlate && (
            <VehicleDetail plate={selectedPlate} api={API} onClose={() => setSelectedPlate(null)} />
          )}
          <AlertFeed alerts={liveAlerts} />
        </div>
      </div>
    </div>
  )
}
