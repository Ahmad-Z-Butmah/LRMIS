import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import StaffLayout from '../../components/StaffLayout'
import MapFilters from '../../components/MapFilters'
import {
  getParcelGeoFeed,
  getPendingApplicationsGeoFeed,
  getDisputedParcels,
  getSurveyTasksGeoFeed,
  getPendingHeatmap,
} from '../../api/mapApi'
import MarkerClusterGroup from 'react-leaflet-cluster'
import 'react-leaflet-cluster/dist/assets/MarkerCluster.css'
import 'react-leaflet-cluster/dist/assets/MarkerCluster.Default.css'
import './LiveMap.css'

// ─── Layer styles ─────────────────────────────────────────────────────────────

const STYLES = {
  parcels:       { color: '#15532D', weight: 1.5, fillColor: 'rgba(21,83,45,0.08)',  fillOpacity: 1 },
  pending:       { color: '#D97706', weight: 1.5, fillColor: 'rgba(217,119,6,0.12)', fillOpacity: 1 },
  surveyReq:     { color: '#F59E0B', weight: 2,   fillColor: 'rgba(245,158,11,0.18)',fillOpacity: 1 },
  disputed:      { color: '#DC2626', weight: 2,   fillColor: 'rgba(220,38,38,0.15)', fillOpacity: 1 },
  surveyTasks:   { color: '#1D4ED8', weight: 1.5, fillColor: 'rgba(29,78,216,0.12)', fillOpacity: 1 },
}

// ─── Fit-bounds helper (runs inside MapContainer context) ─────────────────────

function FitBoundsOnLoad({ geofeeds }) {
  const map = useMap()
  useEffect(() => {
    const allFeatures = Object.values(geofeeds)
      .flatMap((d) => (d?.features || []))
      .filter((f) => f?.geometry)

    if (!allFeatures.length) return
    try {
      const layer = L.geoJSON({ type: 'FeatureCollection', features: allFeatures })
      const bounds = layer.getBounds()
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
      }
    } catch { /* ignore invalid geometry */ }
  }, [])  // only on initial load
  return null
}

// ─── Safe FeatureCollection validator ────────────────────────────────────────

function safeFC(data) {
  if (!data || data.type !== 'FeatureCollection' || !Array.isArray(data.features)) {
    return { type: 'FeatureCollection', features: [] }
  }
  return {
    ...data,
    features: data.features.filter(
      (f) => f && f.type === 'Feature' && f.geometry && f.geometry.type && f.geometry.coordinates
    ),
  }
}

// ─── Apply text filters (zone, status, disputeState) to a FeatureCollection ──

function applyFilters(fc, { zone, status, disputeState }) {
  let features = fc.features
  if (zone)         features = features.filter((f) => f.properties?.zone_id === zone || f.properties?.zone === zone)
  if (status)       features = features.filter((f) => f.properties?.status === status || f.properties?.task_status === status)
  if (disputeState) features = features.filter((f) => f.properties?.dispute_state === disputeState)
  return { ...fc, features }
}

// ─── Selected feature info panel ──────────────────────────────────────────────

function FeaturePanel({ feature, onClose }) {
  if (!feature) return null
  const p = feature.properties || {}

  const rows = Object.entries(p).filter(([, v]) => v !== null && v !== undefined && v !== '')
  return (
    <div className="lm-panel">
      <div className="lm-panel__head">
        <span className="lm-panel__title">Selected Feature</span>
        <button type="button" className="lm-panel__close" onClick={onClose}>✕</button>
      </div>
      <div className="lm-panel__body">
        {rows.map(([k, v]) => (
          <div key={k} className="lm-panel__row">
            <span className="lm-panel__key">{k.replace(/_/g, ' ')}</span>
            <span className="lm-panel__val">{String(v)}</span>
          </div>
        ))}
        {rows.length === 0 && <p className="lm-panel__empty">No properties.</p>}
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

const DEFAULT_FILTERS = {
  showParcels:        true,
  showPending:        true,
  showSurveyRequired: true,
  showDisputed:       true,
  showSurveyTasks:    true,
  showHeatmap:        false,
  zone:           '',
  applicationType:'',
  status:         '',
  disputeState:   '',
}

export default function LiveMap() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [selected, setSelected] = useState(null)

  // Geofeed data
  const [parcels,    setParcels]    = useState(null)
  const [pending,    setPending]    = useState(null)
  const [disputed,   setDisputed]   = useState(null)
  const [surveyTasks,setSurveyTasks]= useState(null)
  const [heatmap,    setHeatmap]    = useState(null)
  const [loadError,  setLoadError]  = useState(null)
  const [dataLoaded, setDataLoaded] = useState(false)

  // Re-fetch from backend whenever text filters change (Task 21 — pass filters to backend via mapApi.js)
  useEffect(() => {
    setDataLoaded(false)
    const backendFilters = {
      zone_id:          filters.zone        || undefined,
      status:           filters.status      || undefined,
      dispute_state:    filters.disputeState|| undefined,
      application_type: filters.applicationType || undefined,
    }
    Promise.all([
      getParcelGeoFeed({ zone_id: backendFilters.zone_id, status: backendFilters.status, dispute_state: backendFilters.dispute_state }),
      getPendingApplicationsGeoFeed({ zone_id: backendFilters.zone_id, status: backendFilters.status, application_type: backendFilters.application_type }),
      getDisputedParcels({ zone_id: backendFilters.zone_id, dispute_state: backendFilters.dispute_state }),
      getSurveyTasksGeoFeed({ zone_id: backendFilters.zone_id, status: backendFilters.status }),
      getPendingHeatmap({ zone_id: backendFilters.zone_id, status: backendFilters.status }),
    ])
      .then(([p, pend, disp, st, heat]) => {
        setParcels(safeFC(p))
        setPending(safeFC(pend))
        setDisputed(safeFC(disp))
        setSurveyTasks(safeFC(st))
        setHeatmap(safeFC(heat))
        setDataLoaded(true)
      })
      .catch((e) => setLoadError(e.message))
  }, [filters.zone, filters.status, filters.disputeState, filters.applicationType])

  // Derived: survey-required is a subset of pending
  const surveyRequired = useMemo(() => {
    if (!pending) return null
    return {
      ...pending,
      features: pending.features.filter((f) => f.properties?.status === 'survey_required'),
    }
  }, [pending])

  // Apply text filters to each layer
  const textFilters = useMemo(() => ({
    zone:         filters.zone,
    status:       filters.status,
    disputeState: filters.disputeState,
  }), [filters.zone, filters.status, filters.disputeState])

  const filteredParcels      = useMemo(() => parcels      ? applyFilters(parcels,      textFilters) : null, [parcels,      textFilters])
  const filteredPending      = useMemo(() => pending      ? applyFilters(pending,      textFilters) : null, [pending,      textFilters])
  const filteredSurveyReq    = useMemo(() => surveyRequired ? applyFilters(surveyRequired, textFilters) : null, [surveyRequired, textFilters])
  const filteredDisputed     = useMemo(() => disputed     ? applyFilters(disputed,     textFilters) : null, [disputed,     textFilters])
  const filteredSurveyTasks  = useMemo(() => surveyTasks  ? applyFilters(surveyTasks,  textFilters) : null, [surveyTasks,  textFilters])

  // Layer key: forces GeoJSON remount when filters change (react-leaflet requirement)
  const layerKey = [filters.zone, filters.status, filters.disputeState].join('-')

  // Click handler factory
  const makeOnEachFeature = useCallback((layerName) => (feature, layer) => {
    layer.on('click', (e) => {
      L.DomEvent.stopPropagation(e)
      setSelected({ ...feature, _layer: layerName })
    })
    layer.on('mouseover', () => { layer.setStyle({ fillOpacity: 0.4, weight: 2.5 }) })
    layer.on('mouseout',  () => { layer.setStyle({ fillOpacity: 1, weight: layer._lmWeight || 1.5 }) })
  }, [])

  // pointToLayer for heatmap Points
  const heatmapPointToLayer = useCallback((feature, latlng) => {
    const intensity = feature.properties?.intensity || 0.3
    const count     = feature.properties?.count || 0
    const radius    = 12 + Math.round(intensity * 20)
    return L.circleMarker(latlng, {
      radius,
      fillColor:   '#7C3AED',
      color:       '#5B21B6',
      weight:      1.5,
      fillOpacity: 0.35 + intensity * 0.45,
    }).bindTooltip(`Zone: ${feature.properties?.zone_id || '?'} — ${count} pending`, { sticky: true })
  }, [])

  // Counts for filter panel
  const counts = useMemo(() => ({
    parcels:       filteredParcels?.features?.length ?? 0,
    pending:       filteredPending?.features?.length ?? 0,
    surveyRequired:filteredSurveyReq?.features?.length ?? 0,
    disputed:      filteredDisputed?.features?.length ?? 0,
    surveyTasks:   filteredSurveyTasks?.features?.length ?? 0,
    heatmap:       heatmap?.features?.length ?? 0,
  }), [filteredParcels, filteredPending, filteredSurveyReq, filteredDisputed, filteredSurveyTasks, heatmap])

  return (
    <StaffLayout>
      <div className="lm-page">

        {/* ── Page header ── */}
        <div className="lm-header">
          <div className="lm-header__left">
            <h1 className="lm-header__title">Live Parcel Map</h1>
            <p className="lm-header__desc">
              Land parcel boundaries, application status, and survey assignments
            </p>
          </div>
          <div className="lm-header__badges">
            <span className="lm-badge lm-badge--green">
              {counts.parcels} Parcels
            </span>
            <span className="lm-badge lm-badge--amber">
              {counts.pending} Pending
            </span>
            <span className="lm-badge lm-badge--red">
              {counts.disputed} Disputed
            </span>
          </div>
        </div>

        {loadError && (
          <div className="alert alert--error" style={{ margin: '0 0 16px' }}>
            Failed to load map data — {loadError}
          </div>
        )}

        {/* ── Main layout: sidebar + map ── */}
        <div className="lm-layout">

          {/* ── Sidebar ── */}
          <div className="lm-sidebar">
            {/* Clustering — active on heatmap point layer */}
            <div className="lm-cluster-active">
              <span className="lm-cluster-active__icon">✓</span>
              <div>
                <strong>Heatmap clustering: ACTIVE</strong>
                <p>
                  Zone points are clustered via <code>react-leaflet-cluster</code>.
                  Parcel, application, and dispute polygon layers render as GeoJSON boundaries (not clustered).
                </p>
              </div>
            </div>

            <MapFilters
              filters={filters}
              onChange={setFilters}
              counts={counts}
            />

            {/* ── Legend ── */}
            <div className="lm-legend">
              <p className="lm-legend__title">Legend</p>
              {[
                { color: '#15532D', label: 'Parcels' },
                { color: '#D97706', label: 'Pending Applications' },
                { color: '#F59E0B', label: 'Survey Required' },
                { color: '#DC2626', label: 'Disputed Parcels' },
                { color: '#1D4ED8', label: 'Survey Tasks' },
                { color: '#7C3AED', label: 'Pending Heatmap' },
              ].map(({ color, label }) => (
                <div key={label} className="lm-legend__row">
                  <span className="lm-legend__swatch" style={{ background: color }} />
                  <span className="lm-legend__label">{label}</span>
                </div>
              ))}
            </div>

            {/* ── Selected feature panel ── */}
            <FeaturePanel
              feature={selected}
              onClose={() => setSelected(null)}
            />
          </div>

          {/* ── Map container ── */}
          <div className="lm-map-wrap">
            {!dataLoaded && !loadError && (
              <div className="lm-map-loading">
                <div className="sv-loading__spinner" />
                <p>Loading map data…</p>
              </div>
            )}

            <MapContainer
              center={[31.9, 35.2]}
              zoom={9}
              style={{ height: '100%', width: '100%' }}
              className="lm-map"
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                maxZoom={19}
              />

              {/* Fit bounds after data loads */}
              {dataLoaded && (
                <FitBoundsOnLoad geofeeds={{ parcels, pending, disputed, surveyTasks }} />
              )}

              {/* Parcel boundaries */}
              {filters.showParcels && filteredParcels?.features?.length > 0 && (
                <GeoJSON
                  key={`parcels-${layerKey}`}
                  data={filteredParcels}
                  style={() => STYLES.parcels}
                  onEachFeature={makeOnEachFeature('Parcel')}
                />
              )}

              {/* Pending applications (non-survey-required subset) */}
              {filters.showPending && filteredPending?.features?.length > 0 && (
                <GeoJSON
                  key={`pending-${layerKey}`}
                  data={{
                    ...filteredPending,
                    features: filteredPending.features.filter(
                      (f) => f.properties?.status !== 'survey_required'
                    ),
                  }}
                  style={() => STYLES.pending}
                  onEachFeature={makeOnEachFeature('Pending Application')}
                />
              )}

              {/* Survey required applications */}
              {filters.showSurveyRequired && filteredSurveyReq?.features?.length > 0 && (
                <GeoJSON
                  key={`surveyreq-${layerKey}`}
                  data={filteredSurveyReq}
                  style={() => STYLES.surveyReq}
                  onEachFeature={makeOnEachFeature('Survey Required')}
                />
              )}

              {/* Disputed parcels */}
              {filters.showDisputed && filteredDisputed?.features?.length > 0 && (
                <GeoJSON
                  key={`disputed-${layerKey}`}
                  data={filteredDisputed}
                  style={() => STYLES.disputed}
                  onEachFeature={makeOnEachFeature('Disputed Parcel')}
                />
              )}

              {/* Survey tasks */}
              {filters.showSurveyTasks && filteredSurveyTasks?.features?.length > 0 && (
                <GeoJSON
                  key={`surveytasks-${layerKey}`}
                  data={filteredSurveyTasks}
                  style={() => STYLES.surveyTasks}
                  onEachFeature={makeOnEachFeature('Survey Task')}
                />
              )}

              {/* Pending heatmap (Points) — wrapped in real marker clustering */}
              {filters.showHeatmap && heatmap?.features?.length > 0 && (
                <MarkerClusterGroup chunkedLoading>
                  <GeoJSON
                    key={`heatmap-${layerKey}`}
                    data={heatmap}
                    pointToLayer={heatmapPointToLayer}
                    onEachFeature={makeOnEachFeature('Heatmap Zone')}
                  />
                </MarkerClusterGroup>
              )}
            </MapContainer>
          </div>
        </div>

        <p className="lm-note">
          Heatmap zone points are clustered via <code>react-leaflet-cluster</code>.
          Parcel, application, and dispute layers render as GeoJSON polygon boundaries.
        </p>

      </div>
    </StaffLayout>
  )
}
