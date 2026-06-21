import React, { useState, useCallback } from 'react'
import { MapContainer, TileLayer, Polygon, Polyline, CircleMarker, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './MapPicker.css'

const DEFAULT_CENTER = [31.95, 35.25]
const DEFAULT_ZOOM   = 9

const COLORS = {
  primary: '#1B4332',
  fill:    '#2D6A4F',
  accent:  '#C9A84C',
  success: '#059669',
}

function ClickLayer({ onAdd, locked }) {
  useMapEvents({
    click(e) {
      if (!locked) onAdd([e.latlng.lng, e.latlng.lat])
    },
  })
  return null
}

export default function MapPicker({ onGeometryChange }) {
  const [points,    setPoints]    = useState([])
  const [confirmed, setConfirmed] = useState(false)

  const handleAdd = useCallback((coord) => {
    setPoints((prev) => [...prev, coord])
  }, [])

  const handleClear = () => {
    setPoints([])
    setConfirmed(false)
    onGeometryChange(null)
  }

  const handleConfirm = () => {
    if (points.length < 3) return
    const closedRing = [...points, points[0]]
    onGeometryChange({ type: 'Polygon', coordinates: [closedRing] })
    setConfirmed(true)
  }

  const leafletPositions = points.map(([lng, lat]) => [lat, lng])
  const canConfirm       = points.length >= 3 && !confirmed
  const remaining        = Math.max(0, 3 - points.length)

  return (
    <div className="map-picker">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: 380, width: '100%' }}
        scrollWheelZoom
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
        />

        <ClickLayer onAdd={handleAdd} locked={confirmed} />

        {points.map(([lng, lat], i) => (
          <CircleMarker
            key={i}
            center={[lat, lng]}
            radius={5}
            pathOptions={{
              color:       confirmed ? COLORS.success : COLORS.primary,
              fillColor:   COLORS.accent,
              fillOpacity: 1,
              weight:      2,
            }}
          />
        ))}

        {points.length >= 3 && (
          <Polygon
            positions={leafletPositions}
            pathOptions={{
              color:       confirmed ? COLORS.success : COLORS.primary,
              fillColor:   confirmed ? COLORS.success : COLORS.fill,
              fillOpacity: 0.2,
              weight:      2,
            }}
          />
        )}

        {points.length >= 2 && points.length < 3 && (
          <Polyline
            positions={leafletPositions}
            pathOptions={{ color: COLORS.primary, weight: 2, dashArray: '6 4' }}
          />
        )}
      </MapContainer>

      <div className="map-controls">
        <span className="map-controls__status">
          {confirmed
            ? `✓ Location confirmed — ${points.length} vertices`
            : remaining > 0
              ? `${points.length} point${points.length !== 1 ? 's' : ''} — click the map to add ${remaining} more`
              : `${points.length} points — ready to confirm`}
        </span>

        <div className="map-controls__actions">
          <button type="button" className="map-btn map-btn--clear" onClick={handleClear}>
            Clear
          </button>
          <button
            type="button"
            className={`map-btn map-btn--confirm${confirmed ? ' map-btn--confirmed' : ''}`}
            onClick={handleConfirm}
            disabled={!canConfirm}
          >
            {confirmed ? '✓ Confirmed' : 'Confirm Location'}
          </button>
        </div>
      </div>
    </div>
  )
}
