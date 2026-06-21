const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'

async function handleResponse(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// Task 9 — GET /staff/{staff_id}/survey-tasks
// Returns { staff_id, tasks: [...], total }
export async function getSurveyorTasks(staffId) {
  const res = await fetch(`${BASE_URL}/staff/${encodeURIComponent(staffId)}/survey-tasks`)
  return handleResponse(res)
}

// Task 6+7 — POST /applications/{application_id}/auto-assign-surveyor
// Returns { application_id, task_id, assigned_surveyor_id, score, status, ... }
export async function autoAssignSurveyor(applicationId) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/auto-assign-surveyor`,
    { method: 'POST' }
  )
  return handleResponse(res)
}

// Task 10 — PATCH /applications/{application_id}/survey-milestone
// payload: { milestone, by, note?, meta? }
// Enforces strict sequential milestone order on backend.
// For visit_scheduled: include meta: { scheduled_date: 'YYYY-MM-DD' }
export async function updateSurveyMilestone(applicationId, payload) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/survey-milestone`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

// NOTE: No dedicated field-notes endpoint exists in the current backend.
// backend/app/routers/survey_reports.py is an empty placeholder router.
// This function targets /applications/{id}/field-notes — ENDPOINT NOT VERIFIED.
// Notes can currently be attached via the `note` field in updateSurveyMilestone.
export async function addFieldNote(applicationId, payload) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/field-notes`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

// POST /applications/{id}/survey-report — VERIFIED.
// Implemented in backend/app/routers/survey_reports.py.
// Payload: { surveyor_id, task_id, field_notes, measurements?, status? }
export async function uploadSurveyReport(applicationId, payload) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/survey-report`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

// NOTE: No registrar review survey endpoint exists in the current backend.
// backend/app/routers/registrar.py is an empty placeholder router.
// This function targets /applications/{id}/registrar-review — ENDPOINT NOT VERIFIED.
// Registrar review of survey is done by advancing milestone to 'registrar_reviewed'
// via updateSurveyMilestone.
export async function registrarReview(applicationId, payload) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/registrar-review`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

// Task 8 — PATCH /applications/{application_id}/reassign-surveyor
// payload: { new_surveyor_id, reassigned_by, reason }
export async function manualReassignSurveyor(applicationId, payload) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/reassign-surveyor`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}
