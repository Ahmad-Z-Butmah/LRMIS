const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'

async function handleResponse(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

function buildQuery(params) {
  const q = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&')
  return q ? `?${q}` : ''
}

// Task 16 + 21 — GET /analytics/geofeeds/parcels
// Optional filters: zone_id, status (registration_status), dispute_state
export async function getParcelGeoFeed(filters = {}) {
  const qs = buildQuery({
    zone_id:       filters.zone_id,
    status:        filters.status,
    dispute_state: filters.dispute_state,
  })
  return handleResponse(await fetch(`${BASE_URL}/analytics/geofeeds/parcels${qs}`))
}

// Task 18 + 21 — GET /analytics/geofeeds/pending-heatmap
// Optional filters: zone_id, status
export async function getPendingHeatmap(filters = {}) {
  const qs = buildQuery({ zone_id: filters.zone_id, status: filters.status })
  return handleResponse(await fetch(`${BASE_URL}/analytics/geofeeds/pending-heatmap${qs}`))
}

// Task 17 + 21 — GET /analytics/geofeeds/pending-applications
// Optional filters: zone_id, status, application_type
export async function getPendingApplicationsGeoFeed(filters = {}) {
  const qs = buildQuery({
    zone_id:          filters.zone_id,
    status:           filters.status,
    application_type: filters.application_type,
  })
  return handleResponse(await fetch(`${BASE_URL}/analytics/geofeeds/pending-applications${qs}`))
}

// survey_required subset — passes status=survey_required to backend
export async function getSurveyRequiredApplications(filters = {}) {
  const data = await getPendingApplicationsGeoFeed({ ...filters, status: 'survey_required' })
  if (data && Array.isArray(data.features)) {
    return {
      ...data,
      features: data.features.filter((f) => f?.properties?.status === 'survey_required'),
    }
  }
  return data
}

// Task 19 + 21 — GET /analytics/geofeeds/disputed-parcels
// Optional filters: zone_id, dispute_state
export async function getDisputedParcels(filters = {}) {
  const qs = buildQuery({
    zone_id:       filters.zone_id,
    dispute_state: filters.dispute_state,
  })
  return handleResponse(await fetch(`${BASE_URL}/analytics/geofeeds/disputed-parcels${qs}`))
}

// Task 20 + 21 — GET /analytics/geofeeds/survey-tasks
// Optional filters: zone_id, status
export async function getSurveyTasksGeoFeed(filters = {}) {
  const qs = buildQuery({ zone_id: filters.zone_id, status: filters.status })
  return handleResponse(await fetch(`${BASE_URL}/analytics/geofeeds/survey-tasks${qs}`))
}

// Task 22 — GET /analytics/geofeeds/nearby
// Requires real MongoDB with 2dsphere index; returns empty features under mongomock
export async function getNearbyParcels(lng, lat, maxDistance = 1000) {
  const qs = `?lng=${lng}&lat=${lat}&max_distance=${maxDistance}`
  return handleResponse(await fetch(`${BASE_URL}/analytics/geofeeds/nearby${qs}`))
}
