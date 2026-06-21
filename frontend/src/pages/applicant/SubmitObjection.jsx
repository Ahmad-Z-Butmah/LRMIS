import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import { fetchApplication, transitionApplication } from '../../api/applicationsApi'
import './SubmitObjection.css'

/*
 * INTEGRATION NOTE (Task 24):
 * The objection endpoint used here is PATCH /applications/{id}/transition
 * with target_state: "under_objection". This is the standard workflow
 * transition approach used in this project.
 *
 * Supporting document attachment is a MOCK placeholder — files are stored
 * in local state only. When a dedicated objection endpoint is available:
 *
 *   import { submitObjectionWithDocs } from '../../api/applicationsApi'
 *   await submitObjectionWithDocs(app.application_id, { ...objectionData, files })
 *
 * Replace the handleSubmit body below with that call.
 */

const OBJECTION_REASONS = [
  { value: 'boundary_dispute',      label: 'Boundary Dispute' },
  { value: 'ownership_claim',       label: 'Ownership Claim' },
  { value: 'incorrect_information', label: 'Incorrect Application Information' },
  { value: 'encroachment',          label: 'Land Encroachment' },
  { value: 'easement_rights',       label: 'Easement Rights Violation' },
  { value: 'other',                 label: 'Other' },
]

const INITIAL_FORM = {
  reason:        '',
  description:   '',
  objectorName:  '',
  objectorId:    '',
}

export default function SubmitObjection() {
  const { id: urlId } = useParams()
  const navigate      = useNavigate()

  // ── Application lookup state ───────────────────────────────────────────────
  const [appId, setAppId]           = useState(urlId || '')
  const [app, setApp]               = useState(null)
  const [appLoading, setAppLoading] = useState(false)
  const [appError, setAppError]     = useState(null)

  // ── Form state ─────────────────────────────────────────────────────────────
  const [form, setForm]               = useState(INITIAL_FORM)
  const [errors, setErrors]           = useState({})
  const [attachments, setAttachments] = useState([]) // mock: [{ name, file }]
  const [submitting, setSubmitting]   = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [success, setSuccess]         = useState(false)

  useEffect(() => {
    if (urlId) loadApp(urlId)
  }, [urlId])

  const loadApp = async (id) => {
    if (!id.trim()) return
    setAppLoading(true)
    setAppError(null)
    setApp(null)
    try {
      const data = await fetchApplication(id.trim())
      setApp(data)
    } catch (e) {
      setAppError(e.message)
    } finally {
      setAppLoading(false)
    }
  }

  const handleLookup = (e) => {
    e.preventDefault()
    loadApp(appId)
  }

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }))
    if (errors[field]) setErrors((err) => ({ ...err, [field]: undefined }))
  }

  // Supporting docs — mock (no real upload)
  const handleAddAttachment = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setAttachments((prev) => [...prev, { name: file.name, file }])
    e.target.value = ''
  }

  const removeAttachment = (idx) => {
    setAttachments((prev) => prev.filter((_, i) => i !== idx))
  }

  const validate = () => {
    const e = {}
    if (!form.reason)                      e.reason       = 'Please select a reason'
    if (form.description.trim().length < 20) e.description = 'Please provide at least 20 characters'
    if (!form.objectorName.trim())         e.objectorName = 'Your full name is required'
    if (!form.objectorId.trim())           e.objectorId   = 'Your National ID is required'
    return e
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setErrors({})
    setSubmitError(null)
    setSubmitting(true)

    try {
      /*
       * Real API call: transition the application to "under_objection".
       * The note field carries the structured objection data.
       *
       * TODO (Task 24 integration): if a dedicated objection endpoint is
       * created, replace this transitionApplication call with it and include
       * the attachments FormData.
       */
      await transitionApplication(app.application_id, {
        target_state: 'under_objection',
        actor_type:   'applicant',
        actor_id:     form.objectorId.trim(),
        note: `[${form.reason}] ${form.description.trim()} — Filed by: ${form.objectorName.trim()}`,
      })
      setSuccess(true)
    } catch (err) {
      /*
       * Fallback: if transition fails (e.g. endpoint not yet deployed or
       * status transition is invalid), show the error but keep the form data.
       */
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  // ── Success state ──────────────────────────────────────────────────────────
  if (success) {
    return (
      <Layout>
        <div className="objection-success">
          <div className="objection-success__card">
            <div className="objection-success__icon">📩</div>
            <h2 className="objection-success__title">Objection Submitted</h2>
            <p className="objection-success__desc">
              Your objection against application{' '}
              <span className="objection-success__id">{app?.application_id}</span>{' '}
              has been recorded. A registry officer will review it and respond to you.
            </p>
            <div className="objection-success__actions">
              <button className="btn btn--primary" onClick={() => navigate('/applicant')}>
                Dashboard
              </button>
              <button
                className="btn btn--outline"
                onClick={() => navigate(`/applicant/track/${app?.application_id}`)}
              >
                Track Application
              </button>
            </div>
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="page-container page-container--sm">
        <div className="page-header">
          <h1>Submit Objection</h1>
          <p>File a formal objection against a land registration application.</p>
        </div>

        {/* ── Step 1: Application lookup ── */}
        <div className="card">
          <h2 className="section-title">Step 1 — Identify Application</h2>
          <form className="objection-lookup-form" onSubmit={handleLookup}>
            <input
              type="text"
              className="form-input"
              placeholder="Enter Application ID"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
            />
            <button type="submit" className="btn btn--primary" disabled={appLoading}>
              {appLoading ? 'Loading…' : 'Load'}
            </button>
          </form>

          {appError && (
            <div className="alert alert--error" style={{ marginTop: 12, marginBottom: 0 }}>{appError}</div>
          )}

          {app && (
            <div className="objection-app-preview">
              <span className="objection-app-id">{app.application_id}</span>
              <StatusBadge status={app.status} />
              <span className="objection-app-parcel">
                Parcel: {typeof app.parcel_ref === 'string'
                  ? app.parcel_ref
                  : app.parcel_ref?.parcel_number || '—'}
              </span>
            </div>
          )}
        </div>

        {/* Show existing objection notice */}
        {app?.objection_status && (
          <div className="objection-existing">
            ⚠ An objection already exists for this application (status: <strong>{app.objection_status.replace(/_/g, ' ')}</strong>).
            Submitting again will update the application state.
          </div>
        )}

        {/* ── Step 2: Objection form (only when app is loaded) ── */}
        {app && (
          <form onSubmit={handleSubmit}>

            {/* Your information */}
            <div className="card">
              <h2 className="section-title">Step 2 — Your Information</h2>
              <div className="form-grid-2">
                <div className="form-field">
                  <label className={`form-label${errors.objectorName ? ' form-label--error' : ''}`}>
                    Full Name <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    className={`form-input${errors.objectorName ? ' form-input--error' : ''}`}
                    placeholder="Your full legal name"
                    value={form.objectorName}
                    onChange={set('objectorName')}
                  />
                  {errors.objectorName && <span className="form-error">{errors.objectorName}</span>}
                </div>

                <div className="form-field">
                  <label className={`form-label${errors.objectorId ? ' form-label--error' : ''}`}>
                    National ID <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    className={`form-input${errors.objectorId ? ' form-input--error' : ''}`}
                    placeholder="Your national ID number"
                    value={form.objectorId}
                    onChange={set('objectorId')}
                  />
                  {errors.objectorId && <span className="form-error">{errors.objectorId}</span>}
                </div>
              </div>
            </div>

            {/* Objection details */}
            <div className="card">
              <h2 className="section-title">Step 3 — Objection Details</h2>
              <div className="objection-form-stack">

                {/* Reason */}
                <div className="form-field">
                  <label className={`form-label${errors.reason ? ' form-label--error' : ''}`}>
                    Reason <span className="required">*</span>
                  </label>
                  <select
                    className={`form-input${errors.reason ? ' form-input--error' : ''}`}
                    value={form.reason}
                    onChange={set('reason')}
                  >
                    <option value="">Select a reason…</option>
                    {OBJECTION_REASONS.map((r) => (
                      <option key={r.value} value={r.value}>{r.label}</option>
                    ))}
                  </select>
                  {errors.reason && <span className="form-error">{errors.reason}</span>}
                </div>

                {/* Description */}
                <div className="form-field">
                  <label className={`form-label${errors.description ? ' form-label--error' : ''}`}>
                    Detailed Description <span className="required">*</span>
                  </label>
                  <textarea
                    rows={6}
                    className={`form-input${errors.description ? ' form-input--error' : ''}`}
                    placeholder="Describe your objection in detail. Include relevant facts, dates, and any supporting information. (minimum 20 characters)"
                    value={form.description}
                    onChange={set('description')}
                  />
                  <div className="char-counter">
                    {errors.description
                      ? <span className="form-error">{errors.description}</span>
                      : <span />
                    }
                    <span className="char-counter__count">{form.description.length} chars</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Supporting documents (mock) */}
            <div className="card">
              <h2 className="section-title">Step 4 — Supporting Documents</h2>
              <div className="objection-attach-list">
                {attachments.map((att, i) => (
                  <div key={i} className="objection-attach-item">
                    <span>📄</span>
                    <span className="objection-attach-item__name">{att.name}</span>
                    <button
                      type="button"
                      className="objection-attach-remove"
                      onClick={() => removeAttachment(i)}
                      title="Remove"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>

              <label className="objection-attach-add">
                + Attach Document
                <input
                  type="file"
                  style={{ display: 'none' }}
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  onChange={handleAddAttachment}
                />
              </label>

              <p className="objection-attach-hint">
                Optional — attach evidence such as deeds, maps, or photos.
              </p>

              {/*
               * TODO (Task 24 integration): When a real objection endpoint
               * is ready, include `attachments.map(a => a.file)` in the
               * FormData payload sent to the backend.
               */}
              <div className="objection-mock-notice">
                ℹ Attached files are currently stored locally only (preview mode).
                Full document upload will be enabled when the backend endpoint is available.
              </div>
            </div>

            {/* Submission error */}
            {submitError && (
              <div className="alert alert--error">
                Submission failed: {submitError}
              </div>
            )}

            {/* Form footer */}
            <div className="objection-form-footer">
              <button
                type="button"
                className="btn btn--muted"
                onClick={() => navigate('/applicant')}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn--danger btn--lg"
                disabled={submitting}
              >
                {submitting ? 'Submitting…' : 'Submit Objection →'}
              </button>
            </div>

          </form>
        )}
      </div>
    </Layout>
  )
}
