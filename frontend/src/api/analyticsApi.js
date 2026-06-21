const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'

async function handleResponse(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// Internal: paginate all applications.
// No dedicated /analytics/applications-by-status or /analytics/applications-by-zone
// endpoint exists — derived client-side from GET /applications/.
async function fetchAllApplications() {
  const first = await handleResponse(await fetch(`${BASE_URL}/applications/?limit=100&page=1`))
  const items = [...(first.items || [])]
  const totalPages = first.total > 0 ? Math.ceil(first.total / 100) : 1
  if (totalPages > 1) {
    const pages = await Promise.all(
      Array.from({ length: totalPages - 1 }, (_, i) =>
        fetch(`${BASE_URL}/applications/?limit=100&page=${i + 2}`).then(handleResponse)
      )
    )
    pages.forEach((r) => items.push(...(r.items || [])))
  }
  return items
}

// Task 30.1 — GET /analytics/kpis  [VERIFIED]
// Returns: { total_applications, pending_applications, survey_required,
//            approved_count, rejected_count, certificates_issued,
//            active_surveyors, active_survey_tasks }
export async function getKpis() {
  return handleResponse(await fetch(`${BASE_URL}/analytics/kpis`))
}

// Task 30.2 + 30.3 + "applications over time" — DERIVED from GET /applications/
// byZone uses GET /analytics/geofeeds/pending-applications (Option A) which carries
// real zone_id in feature.properties — reliable even when parcel_ref is a string.
// byStatus and overTime still come from paginated GET /applications/.
// Returns: { byStatus, byZone, overTime, byZoneSource }
export async function getApplicationsDerived() {
  // Fetch in parallel: all applications (for status + time) + pending geofeed (for zone)
  const [items, pendingGeoFeed] = await Promise.all([
    fetchAllApplications(),
    fetch(`${BASE_URL}/analytics/geofeeds/pending-applications`)
      .then(handleResponse)
      .catch(() => null),   // non-blocking — fall back to parcel_ref if unavailable
  ])

  const statusMap = {}
  const timeMap   = {}

  items.forEach((a) => {
    const s = a.status || 'unknown'
    statusMap[s] = (statusMap[s] || 0) + 1

    const d = a.submitted_at || a.created_at
    if (d) {
      const month = String(d).substring(0, 7)
      if (/^\d{4}-\d{2}$/.test(month)) {
        timeMap[month] = (timeMap[month] || 0) + 1
      }
    }
  })

  // Zone: primary = pending-applications geofeed (has zone_id in properties)
  // Fallback = parcel_ref.zone_id from applications (unreliable when parcel_ref is a string)
  const zoneMap = {}
  let byZoneSource = 'parcel_ref_fallback'

  if (pendingGeoFeed?.features?.length) {
    byZoneSource = 'geofeed:pending-applications'
    pendingGeoFeed.features.forEach((f) => {
      const zone = f?.properties?.zone_id || 'unknown'
      zoneMap[zone] = (zoneMap[zone] || 0) + 1
    })
  } else {
    // Fallback only — zone will be "unknown" when parcel_ref is a plain string
    items.forEach((a) => {
      const pr = a.parcel_ref
      const zone = (pr && typeof pr === 'object' ? pr.zone_id : null) || 'unknown'
      zoneMap[zone] = (zoneMap[zone] || 0) + 1
    })
  }

  return {
    byStatus: Object.entries(statusMap)
      .map(([status, count]) => ({ status, count }))
      .sort((a, b) => b.count - a.count),
    byZone: Object.entries(zoneMap)
      .map(([zone, count]) => ({ zone, count }))
      .sort((a, b) => b.count - a.count),
    overTime: Object.entries(timeMap)
      .map(([month, count]) => ({ month, count }))
      .sort((a, b) => a.month.localeCompare(b.month)),
    byZoneSource,
  }
}

// Named single-result exports per task spec — both delegate to getApplicationsDerived
// (causes two separate fetches if called individually; use getApplicationsDerived in dashboard)
export async function getApplicationsByStatus() {
  return (await getApplicationsDerived()).byStatus
}

export async function getApplicationsByZone() {
  return (await getApplicationsDerived()).byZone
}

// Task 30.4 / Task 9 — GET /analytics/processing-time
// Returns: [{ application_type, average_processing_days, average_precheck_days,
//             average_survey_delay_days, average_approval_days, sample_count }]
//           sorted by sample_count descending; all 6 known types always included.
export async function getProcessingTime() {
  return handleResponse(await fetch(`${BASE_URL}/analytics/processing-time`))
}

// Task 30.5 — GET /analytics/surveyors  [VERIFIED]
// Returns: { surveyors: [{ surveyor_id, surveyor_name, active_tasks, completed_tasks,
//             max_tasks, workload_percentage, reports_uploaded,
//             reports_uploaded_source, average_task_completion_days }], total }
export async function getSurveyorAnalytics() {
  return handleResponse(await fetch(`${BASE_URL}/analytics/surveyors`))
}

// Task 30.6 — GET /analytics/registrars  [VERIFIED]
// Returns: { registrars: [{ registrar_id, registrar_name, assigned_reviews,
//             assigned_reviews_is_proxy, completed_reviews, approved_count,
//             rejected_count, average_review_time }], total }
export async function getRegistrarAnalytics() {
  return handleResponse(await fetch(`${BASE_URL}/analytics/registrars`))
}

// Task 31 — GET /analytics/certificates-per-month  [VERIFIED]
// Returns: [{ month, count }] sorted ascending by YYYY-MM
export async function getCertificatesPerMonth() {
  return handleResponse(await fetch(`${BASE_URL}/analytics/certificates-per-month`))
}

// Task 10 — GET /analytics/delayed-applications?days=7
// Returns: [{ application_id, status, application_type, parcel_number, zone_id,
//             submitted_at, delayed_days }] sorted by delayed_days descending.
// Terminal statuses excluded: closed, rejected, certificate_issued.
export async function getDelayedApplications(days = 7) {
  return handleResponse(await fetch(`${BASE_URL}/analytics/delayed-applications?days=${days}`))
}
