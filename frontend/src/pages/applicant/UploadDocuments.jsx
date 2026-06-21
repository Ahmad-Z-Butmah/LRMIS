import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import { fetchApplication } from '../../api/applicationsApi'
import './UploadDocuments.css'

/*
 * INTEGRATION NOTE (Task 23):
 * Real document upload is not implemented — the backend upload endpoint
 * is owned by another student and may not yet be available.
 *
 * Current behaviour:
 *  - Files are selected locally and stored in component state.
 *  - On "Submit Documents", the mock flow simulates a successful upload.
 *
 * When the real endpoint is ready, replace the `handleSubmit` function body with:
 *   await uploadDocuments(app.application_id, selectedFiles)
 *   where uploadDocuments() should be added to applicationsApi.js.
 */

const DOCUMENT_OPTIONS = [
  { id: 'national_id',               label: 'National Identity Card',         required: true  },
  { id: 'title_deed',                label: 'Title Deed / Land Certificate',   required: true  },
  { id: 'property_map',              label: 'Property Map / Survey Plan',      required: true  },
  { id: 'power_of_attorney',         label: 'Power of Attorney',               required: false },
  { id: 'land_survey_report',        label: 'Land Survey Report',              required: false },
  { id: 'municipality_permit',       label: 'Municipality / Authority Permit', required: false },
  { id: 'tax_clearance_certificate', label: 'Tax Clearance Certificate',       required: false },
]

export default function UploadDocuments() {
  const navigate       = useNavigate()
  const [searchParams] = useSearchParams()

  const [appId, setAppId]         = useState(searchParams.get('appId') || '')
  const [app, setApp]             = useState(null)
  const [appLoading, setAppLoading] = useState(false)
  const [appError, setAppError]   = useState(null)

  // files: { [docId]: File }
  const [files, setFiles]           = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted]   = useState(false)

  useEffect(() => {
    const id = searchParams.get('appId')
    if (id) loadApp(id)
  }, [])

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

  const handleSearch = (e) => {
    e.preventDefault()
    loadApp(appId)
  }

  const handleFileChange = (docId, file) => {
    setFiles((prev) => {
      const next = { ...prev }
      if (file) next[docId] = file
      else delete next[docId]
      return next
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)

    /*
     * ─────────────────────────────────────────────────────────────────────────
     * TODO (Task 23 integration): Replace the setTimeout below with a real
     * API call when the document upload endpoint is available.
     *
     *   import { uploadDocuments } from '../../api/applicationsApi'
     *   await uploadDocuments(app.application_id, files)
     *
     * The uploadDocuments function should POST FormData with each file keyed
     * by its document type ID (e.g. { national_id: File, title_deed: File }).
     * ─────────────────────────────────────────────────────────────────────────
     */
    await new Promise((r) => setTimeout(r, 900)) // mock delay
    setSubmitting(false)
    setSubmitted(true)
  }

  // Which docs to show: use app.required_documents if available, else show all
  const displayDocs = app?.required_documents?.length
    ? DOCUMENT_OPTIONS.filter((d) => app.required_documents.includes(d.id))
    : DOCUMENT_OPTIONS

  const fileCount    = Object.keys(files).length
  const requiredDocs = displayDocs.filter((d) => d.required)
  const requiredMet  = requiredDocs.every((d) => files[d.id])

  // ── Success state ──────────────────────────────────────────────────────────
  if (submitted) {
    return (
      <Layout>
        <div className="upload-success">
          <div className="upload-success__card">
            <div className="upload-success__icon">📂</div>
            <h2 className="upload-success__title">Documents Submitted</h2>
            <p className="upload-success__desc">
              {fileCount} document(s) have been registered for application{' '}
              <span className="upload-success__id">{app?.application_id}</span>.
              A registry staff member will review them and update your application status.
            </p>
            <div className="upload-success__actions">
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
      <div className="page-container page-container--md">
        <div className="page-header">
          <h1>Upload Documents</h1>
          <p>Enter your Application ID and attach the required supporting documents.</p>
        </div>

        {/* ── Application lookup ── */}
        <div className="card">
          <h2 className="section-title">Application</h2>
          <form className="upload-search-form" onSubmit={handleSearch}>
            <input
              type="text"
              className="form-input"
              placeholder="Enter Application ID"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
            />
            <button type="submit" className="btn btn--primary" disabled={appLoading}>
              {appLoading ? 'Loading…' : 'Load Application'}
            </button>
          </form>

          {appError && <div className="alert alert--error" style={{ marginTop: 12, marginBottom: 0 }}>{appError}</div>}

          {app && (
            <div className="upload-app-info" style={{ marginTop: 16 }}>
              <div>
                <div className="upload-app-id-label">Loaded Application</div>
                <span className="upload-app-id-code">{app.application_id}</span>
              </div>
              <StatusBadge status={app.status} />
              <span className="upload-app-ref">Ref: {app.applicant_ref}</span>
            </div>
          )}
        </div>

        {app && (
          <>
            {/* Warning for missing_documents status */}
            {app.status === 'missing_documents' && (
              <div className="alert alert--warning">
                ⚠ Your application has been flagged — documents are missing. Please upload all required files below to continue.
              </div>
            )}

            {/* Mock notice */}
            <div className="upload-mock-notice">
              <span className="upload-mock-notice__icon">ℹ</span>
              <span>
                File upload is currently in preview mode. Files are selected locally and registered as metadata.
                Actual file storage will be enabled when the upload endpoint is deployed.
              </span>
            </div>

            <form onSubmit={handleSubmit}>
              {/* ── Document list ── */}
              <div className="card">
                <h2 className="section-title">
                  Required Documents
                  {displayDocs.length > 0 && (
                    <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--color-muted)', marginLeft: 8, textTransform: 'none', letterSpacing: 0 }}>
                      ({displayDocs.filter((d) => d.required).length} required)
                    </span>
                  )}
                </h2>
                <div className="upload-doc-list">
                  {displayDocs.map((doc) => {
                    const file     = files[doc.id]
                    const selected = !!file
                    return (
                      <div key={doc.id} className={`upload-doc-row${selected ? ' upload-doc-row--selected' : ''}`}>
                        <div className="upload-doc-info">
                          <div className="upload-doc-name">
                            {doc.label}
                            {doc.required && (
                              <span style={{ color: 'var(--color-error)', marginLeft: 4, fontSize: 12 }}>*</span>
                            )}
                          </div>
                          {selected
                            ? <div className="upload-doc-filename">✓ {file.name}</div>
                            : <div className="upload-doc-status">No file chosen</div>
                          }
                        </div>
                        <label className={`upload-doc-btn${selected ? ' upload-doc-btn--change' : ''}`}>
                          {selected ? 'Change' : 'Choose File'}
                          <input
                            type="file"
                            style={{ display: 'none' }}
                            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                            onChange={(e) => handleFileChange(doc.id, e.target.files[0] || null)}
                          />
                        </label>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="upload-footer">
                <p className="upload-count">
                  {fileCount} of {displayDocs.length} document(s) selected
                  {!requiredMet && fileCount > 0 && (
                    <span style={{ color: 'var(--color-error)', marginLeft: 8 }}>
                      — required documents missing
                    </span>
                  )}
                </p>
                <button
                  type="submit"
                  className="btn btn--primary btn--lg"
                  disabled={fileCount === 0 || submitting}
                >
                  {submitting ? 'Submitting…' : 'Submit Documents →'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </Layout>
  )
}
