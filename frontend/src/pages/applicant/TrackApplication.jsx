import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import Timeline from '../../components/Timeline'
import { getApplicationById } from '../../api/applicationsApi'
import './TrackApplication.css'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

function parcelLabel(ref) {
  if (!ref) return '—'
  if (typeof ref === 'string') return ref
  return ref.parcel_number || '—'
}

function isPublicNote(note) {
  if (!note.visibility) return false
  return note.visibility === 'public' || note.visibility === 'applicant'
}

export default function TrackApplication() {
  const { id }   = useParams()
  const navigate = useNavigate()

  const [searchId, setSearchId] = useState(id || '')
  const [app, setApp]           = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)

  useEffect(() => {
    if (id) load(id)
  }, [id])

  const load = async (appId) => {
    if (!appId.trim()) return
    setLoading(true)
    setError(null)
    setApp(null)
    try {
      const data = await getApplicationById(appId.trim())
      setApp(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    if (!searchId.trim()) return
    navigate(`/applicant/track/${searchId.trim()}`)
    load(searchId.trim())
  }

  const publicNotes  = app?.internal_notes?.filter(isPublicNote) || []
  const hasDocuments = app?.documents?.length > 0

  return (
    <Layout>
      <div className="page-container page-container--md">

        {/* ── Search section — large hero when no app loaded ── */}
        {!app && !loading && (
          <div className="track-search-hero">
            <h1 className="track-search-hero__title">Track Your Application</h1>
            <p className="track-search-hero__desc">
              Enter your Application ID to view current status and processing history.
            </p>
            <form className="track-search-form" onSubmit={handleSearch}>
              <input
                type="text"
                className="form-input track-search-hero__input"
                placeholder="Enter Application ID  (e.g. APP-XXXXXXXX)"
                value={searchId}
                onChange={(e) => setSearchId(e.target.value)}
                autoFocus
              />
              <button type="submit" className="btn btn--primary btn--lg" disabled={loading}>
                Search
              </button>
            </form>
          </div>
        )}

        {/* ── Compact search when app is shown ── */}
        {app && !loading && (
          <form className="track-search-form track-search-form--compact" onSubmit={handleSearch}>
            <input
              type="text"
              className="form-input"
              placeholder="Search another Application ID…"
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
            />
            <button type="submit" className="btn btn--outline" disabled={loading}>
              Search
            </button>
          </form>
        )}

        {/* ── Loading ── */}
        {loading && (
          <div className="card">
            <div className="track-loading">
              <div className="track-loading-spinner" />
              Looking up application…
            </div>
          </div>
        )}

        {/* ── Error ── */}
        {error && !loading && (
          <div className="alert alert--error">
            Application not found or could not be loaded — {error}
          </div>
        )}

        {/* ── Application results ── */}
        {app && !loading && (
          <>
            {/* Status hero card */}
            <div className="track-status-hero">
              <div className="track-status-hero__left">
                <div className="track-id-label">Application ID</div>
                <code className="track-id-code">{app.application_id}</code>
              </div>
              <div className="track-status-hero__right">
                <div className="track-id-label">Current Status</div>
                <StatusBadge status={app.status} />
              </div>
            </div>

            {/* Application meta */}
            <div className="card">
              <div className="track-meta-grid">
                {[
                  { label: 'Parcel Number', value: parcelLabel(app.parcel_ref) },
                  { label: 'Applicant Ref',  value: app.applicant_ref },
                  { label: 'Submitted',      value: formatDate(app.submitted_at) },
                  { label: 'Last Updated',   value: formatDate(app.updated_at) },
                ].map(({ label, value }) => (
                  <div key={label} className="track-meta-item">
                    <div className="track-meta-label">{label}</div>
                    <div className="track-meta-value">{value || '—'}</div>
                  </div>
                ))}
              </div>

              <div className="track-actions">
                {app.status === 'missing_documents' && (
                  <button
                    className="btn btn--warning"
                    onClick={() => navigate(`/applicant/upload?appId=${app.application_id}`)}
                  >
                    Upload Missing Documents
                  </button>
                )}
                <button
                  className="btn btn--outline"
                  onClick={() => navigate(`/applicant/objection/${app.application_id}`)}
                >
                  Submit Objection
                </button>
              </div>
            </div>

            {/* Processing status overview */}
            {(app.survey_status || app.objection_status || app.certificate_status) && (
              <div className="card">
                <h2 className="section-title">Processing Status</h2>
                <div className="track-status-row">
                  {app.survey_status && (
                    <div className="track-status-pill">
                      <span className="track-status-pill__label">Survey</span>
                      <span className="track-status-pill__value">
                        {app.survey_status.replace(/_/g, ' ')}
                      </span>
                    </div>
                  )}
                  {app.objection_status && (
                    <div className="track-status-pill">
                      <span className="track-status-pill__label">Objection</span>
                      <span className="track-status-pill__value">
                        {app.objection_status.replace(/_/g, ' ')}
                      </span>
                    </div>
                  )}
                  {app.certificate_status && (
                    <div className="track-status-pill">
                      <span className="track-status-pill__label">Certificate</span>
                      <span className="track-status-pill__value">
                        {app.certificate_status.replace(/_/g, ' ')}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Documents */}
            {hasDocuments && (
              <div className="card">
                <h2 className="section-title">Documents</h2>
                <div className="track-doc-list">
                  {app.documents.map((doc) => (
                    <div
                      key={doc.name}
                      className={`track-doc-item ${doc.submitted ? 'track-doc-item--submitted' : 'track-doc-item--pending'}`}
                    >
                      <span className="track-doc-icon">{doc.submitted ? '✓' : '○'}</span>
                      <span className="track-doc-name">{doc.name.replace(/_/g, ' ')}</span>
                      <span className={`track-doc-badge ${doc.submitted ? 'track-doc-badge--submitted' : 'track-doc-badge--pending'}`}>
                        {doc.submitted ? 'Submitted' : 'Pending'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Registry notes (applicant-visible only) */}
            {publicNotes.length > 0 && (
              <div className="card">
                <h2 className="section-title">Notes from Registry</h2>
                <div className="track-notes-list">
                  {publicNotes.map((note, i) => (
                    <div key={i} className="track-note">
                      <div className="track-note__meta">
                        {note.author && <span>From: {note.author}</span>}
                        {note.created_at && <span>{formatDate(note.created_at)}</span>}
                      </div>
                      <p className="track-note__text">{note.content || note.text || note.note}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Status timeline */}
            <div className="card">
              <h2 className="section-title">Status Timeline</h2>
              <Timeline
                currentStatus={app.status}
                auditTimeline={app.audit_timeline}
              />
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}
