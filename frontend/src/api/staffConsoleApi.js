const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'

async function handleResponse(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Student 1: Application CRUD & Workflow ─────────────────────────────────

export async function getApplications(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') query.append(k, String(v))
  })
  const url = query.toString()
    ? `${BASE_URL}/applications/?${query}`
    : `${BASE_URL}/applications/`
  const res = await fetch(url)
  return handleResponse(res)
}

export async function getApplicationById(applicationId) {
  const res = await fetch(`${BASE_URL}/applications/${encodeURIComponent(applicationId)}`)
  return handleResponse(res)
}

export async function transitionApplication(applicationId, payload) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/transition`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

export async function holdApplication(applicationId, payload = {}) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/hold`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

export async function rejectApplication(applicationId, payload = {}) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/reject`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

export async function markMissingDocuments(applicationId, payload = {}) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/missing-documents`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

export async function generateCertificate(applicationId, payload = {}) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/certificate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

// ── Student 2: Applicant, Timeline & Document Review ──────────────────────

export async function getApplicantById(applicantId) {
  const res = await fetch(`${BASE_URL}/applicants/${encodeURIComponent(applicantId)}`)
  return handleResponse(res)
}

export async function getApplicationTimeline(applicationId) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/timeline`
  )
  return handleResponse(res)
}

export async function addComment(applicationId, payload) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/comments`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}

export async function getApplicationDocuments(applicationId) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/documents`
  )
  return handleResponse(res)
}

export async function getApplicationComments(applicationId) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/comments`
  )
  return handleResponse(res)
}

export async function reviewDocument(applicationId, documentId, payload) {
  const res = await fetch(
    `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/documents/${encodeURIComponent(documentId)}/review`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  return handleResponse(res)
}
