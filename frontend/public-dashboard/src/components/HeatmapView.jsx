import { useEffect, useRef } from 'react'
import L from 'leaflet'

// Guardian uses pixel-space coordinates from the video feed.
// We map them onto a dummy tile-less Leaflet canvas for the demo.
// In production, replace with real GPS coordinates.

const CANVAS_W = 1280
const CANVAS_H = 720

function riskColor(score) {
  if (score > 100) return '#ef4444'
  if (score > 50) return '#f97316'
  if (score > 20) return '#eab308'
  return '#22c55e'
}

export default function HeatmapView({ zones }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const layerRef = useRef(null)

  useEffect(() => {
    if (mapInstanceRef.current) return
    const map = L.map(mapRef.current, {
      crs: L.CRS.Simple,
      minZoom: -2,
      maxZoom: 4,
    })
    const bounds = [[0, 0], [CANVAS_H, CANVAS_W]]
    L.rectangle(bounds, { color: '#1e293b', fillColor: '#1e293b', fillOpacity: 1 }).addTo(map)
    map.fitBounds(bounds)
    mapInstanceRef.current = map
    layerRef.current = L.layerGroup().addTo(map)
  }, [])

  useEffect(() => {
    if (!mapInstanceRef.current) return
    layerRef.current.clearLayers()
    zones.forEach(z => {
      L.circleMarker([CANVAS_H - z.y, z.x], {
        radius: Math.min(6 + z.incident_count * 2, 30),
        color: riskColor(z.risk_score),
        fillColor: riskColor(z.risk_score),
        fillOpacity: 0.65,
        weight: 1,
      })
        .bindTooltip(`Risk: ${z.risk_score} | Incidents: ${z.incident_count}`, { direction: 'top' })
        .addTo(layerRef.current)
    })
  }, [zones])

  return <div ref={mapRef} className="w-full h-full min-h-[500px]" />
}
