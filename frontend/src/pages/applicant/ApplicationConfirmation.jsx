import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Polygon } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import './ApplicationConfirmation.css'

// Map current status → guidance message shown to applicant
const NEXT_STEP = {
  submitted:          { icon: '🔍', text: 'Your application is pending initial pre-check by registry staff. You will be notified if any documents are missing.' },
  pre_checked:        { icon: '📋', text: 'Your application passed initial review. It may proceed to a land survey or legal review stage shortly.' },
  missing_documents:  { icon: '⚠️', text: 'Action required — your application is on hold. Please upload the missing documents to continue processing.' },
  survey_required:    { icon: '📐', text: 'A land survey has been requested for your parcel. A certified surveyor will be assigned and may contact you.' },
  surveyed:           { icon: '⚖️', text: 'The land survey is complete. Your application has moved to legal review.' },
  legal_review:       { icon: '⚖️', text: 'Your application is under legal review by the registry legal team.' },
  on_hold:            { icon: '⏸️', text: 'Your application is currently on hold. Please contact the registry office for more information.' },
  under_objection:    { icon: '📩', text: 'An objection has been filed against this application. The registry will review and respond.' },
  approved:           { icon: '✅', text: 'Your application has been approved! A land registration certificate will be issued.' },
  certificate_issued: { icon: '🏆', text: 'Congratulations — your land registration certificate has been issued. You may collect it from the registry office.' },
  rejected:           { icon: '❌', text: 'Your application has been rejected. Please visit the registry office for further guidance.' },
  closed:             { icon: '🔒', text: 'This application has been closed.' },
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function getParcelField(ref, field) {
  if (!ref || typeof ref === 'string') return null
  return ref[field] || null
}

// Extract GeoJSON Polygon geometry from parcel_ref object or parcel_data
function extractGeometry(app) {
  const ref = app.parcel_ref
  if (ref && typeof ref === 'object' && ref.geometry?.type === 'Polygon') {
    return ref.geometry
  }
  if (app.parcel_data?.geometry?.type === 'Polygon') {
    return app.parcel_data.geometry
  }
  return null
}

// GeoJSON ring: [[lng, lat], ...] → Leaflet: [[lat, lng], ...]
function toLeafletPositions(ring) {
  return ring.map(([lng, lat]) => [lat, lng])
}

function getCenter(positions) {
  const n = positions.length
  return [
    positions.reduce((s, [lat]) => s + lat, 0) / n,
    positions.reduce((s, [, lng]) => s + lng, 0) / n,
  ]
}

function ParcelMap({ geometry }) {
  if (!geometry) {
    return (
      <div className="confirm-map-no-location">
        <div className="confirm-map-no-location__icon">🗺️</div>
        No parcel location available
      </div>
    )
  }

  const positions = toLeafletPositions(geometry.coordinates[0])
  const center    = getCenter(positions)

  return (
    <div className="confirm-map-wrapper">
      <MapContainer
        center={center}
        zoom={15}
        style={{ height: 300, width: '100%' }}
        scrollWheelZoom={false}
        dragging={false}
        zoomControl={false}
        doubleClickZoom={false}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
        />
        <Polygon
          positions={positions}
          pathOptions={{ color: '#1B4332', fillColor: '#2D6A4F', fillOpacity: 0.25, weight: 2 }}
        />
      </MapContainer>
    </div>
  )
}

export default function ApplicationConfirmation() {
  const { state } = useLocation()
  const navigate  = useNavigate()
  const app       = state?.application

  // ── Fallback: no router state ──────────────────────────────────────────────
  if (!app) {
    return (
      <Layout>
        <div className="confirm-empty">
          <div className="confirm-empty__card">
            <div className="confirm-empty__icon">📋</div>
            <h2 className="confirm-empty__title">No Application Data</h2>
            <p className="confirm-empty__desc">
              This page is shown after submitting a new application.
              If you are looking for an existing application, use Track Application to search by ID.
            </p>
            <div className="confirm-empty__actions">
              <button className="btn btn--primary" onClick={() => navigate('/applicant')}>
                Dashboard
              </button>
              <button className="btn btn--outline" onClick={() => navigate('/applicant/track')}>
                Track Application
              </button>
            </div>
          </div>
        </div>
      </Layout>
    )
  }

  const nextStep  = NEXT_STEP[app.status] || { icon: '📋', text: 'Your application is being processed.' }
  const parcelRef = app.parcel_ref
  const geometry  = extractGeometry(app)

  // Parcel detail fields (only when parcel_ref is an object from submit)
  const parcelFields = typeof parcelRef === 'object' && parcelRef ? [
    { label: 'Parcel No.',  value: parcelRef.parcel_number },
    { label: 'Block No.',   value: parcelRef.block_number },
    { label: 'Basin No.',   value: parcelRef.basin_number },
    { label: 'Zone ID',     value: parcelRef.zone_id },
  ].filter((f) => f.value) : []

  // Read from top-level app field first; fall back to embedded parcel_ref value
  const applicationType =
    (app.application_type || getParcelField(parcelRef, 'application_type'))
      ?.replace(/_/g, ' ') || '—'

  const applicationDetails = [
    { label: 'Application ID',    value: <code>{app.application_id}</code> },
    { label: 'Applicant Ref',     value: app.applicant_ref },
    { label: 'Application Type',  value: applicationType },
    { label: 'Submitted At',      value: formatDate(app.submitted_at) },
    { label: 'Documents',         value: app.required_documents?.length ? `${app.required_documents.length} document identifier(s) registered` : 'None' },
  ]

  return (
    <Layout>
      <div className="page-container page-container--xs confirm-page-container">

        {/* ── Success hero ── */}
        <div className="confirm-hero">
          <div className="confirm-hero__icon"><span>✓</span></div>
          <h1 className="confirm-hero__title">Application Submitted!</h1>
          <p className="confirm-hero__desc">
            Your land registration application has been received and is being processed.
          </p>
        </div>

        {/* ── Application ID + status ── */}
        <div className="card confirm-id-card">
          <div className="confirm-id-label">Application ID</div>
          <div className="confirm-id-value">{app.application_id}</div>
          <StatusBadge status={app.status} />
          <p className="confirm-id-hint">Save this ID — you will need it to track your application.</p>
        </div>

        {/* ── What happens next ── */}
        <div className="card confirm-next">
          <h2 className="confirm-next__title">What Happens Next</h2>
          <div className="confirm-next__message">
            <span className="confirm-next__icon">{nextStep.icon}</span>
            <p className="confirm-next__text">{nextStep.text}</p>
          </div>
          {app.workflow?.allowed_next?.length > 0 && (
            <p className="confirm-next__hint">
              Expected next stages: {app.workflow.allowed_next.map((s) => s.replace(/_/g, ' ')).join(' → ')}
            </p>
          )}
        </div>

        {/* ── Application details ── */}
        <div className="card">
          <h2 className="section-title">Application Details</h2>
          {applicationDetails.map(({ label, value }) => (
            <div key={label} className="confirm-row">
              <span className="confirm-row__label">{label}</span>
              <span className="confirm-row__value">{value}</span>
            </div>
          ))}
        </div>

        {/* ── Parcel information (only when data available) ── */}
        {parcelFields.length > 0 && (
          <div className="card">
            <h2 className="section-title">Parcel Information</h2>
            <div className="confirm-parcel-grid">
              {parcelFields.map(({ label, value }) => (
                <div key={label} className="confirm-parcel-item">
                  <div className="confirm-parcel-item__label">{label}</div>
                  <div className="confirm-parcel-item__value">{value}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Parcel location map ── */}
        <div className="card">
          <h2 className="section-title">Parcel Location</h2>
          <ParcelMap geometry={geometry} />
        </div>

        {/* ── Actions ── */}
        <div className="confirm-actions">
          <button className="btn btn--primary" onClick={() => navigate('/applicant')}>
            Go to Dashboard
          </button>
          <button
            className="btn btn--outline"
            onClick={() => navigate(`/applicant/track/${app.application_id}`)}
          >
            Track This Application
          </button>
        </div>
      </div>
    </Layout>
  )
}
