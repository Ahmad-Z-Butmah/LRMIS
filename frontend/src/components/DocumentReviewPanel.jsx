import React, { useState, useEffect } from 'react'
import { getApplicationDocuments, reviewDocument } from '../api/staffConsoleApi'
import './DocumentReviewPanel.css'

const ACTOR_ID = 'staff_console'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

function statusBadge(s) {
  if (!s) return { label: '—', cls: '' }
  const map = {
    pending_review: { label: 'Pending Review', cls: 'drp__badge--pending' },
    verified:       { label: 'Verified',        cls: 'drp__badge--ok' },
    rejected:       { label: 'Rejected',        cls: 'drp__badge--rejected' },
    uploaded:       { label: 'Uploaded',        cls: 'drp__badge--pending' },
    missing:        { label: 'Missing',         cls: 'drp__badge--rejected' },
  }
  return map[s] || { label: s, cls: '' }
}

export default function DocumentReviewPanel({ documents = [], applicationId, onRefresh }) {
  const [realDocs, setRealDocs]     = useState([])
  const [loadErr,  setLoadErr]      = useState(null)
  const [loadDone, setLoadDone]     = useState(false)

  const [reviewNote, setReviewNote] = useState({})
  const [busy,       setBusy]       = useState({})
  const [docErr,     setDocErr]     = useState({})

  useEffect(() => {
    if (!applicationId) return
    setLoadErr(null)
    setLoadDone(false)
    getApplicationDocuments(applicationId)
      .then((list) => {
        setRealDocs(list || [])
        setLoadDone(true)
      })
      .catch((e) => {
        setLoadErr(e.message)
        setLoadDone(true)
      })
  }, [applicationId])

  async function doReview(doc, reviewStatus) {
    const id = doc.document_id
    setBusy((prev) => ({ ...prev, [id]: true }))
    setDocErr((prev) => ({ ...prev, [id]: null }))
    try {
      await reviewDocument(applicationId, id, {
        status:      reviewStatus,
        reviewed_by: ACTOR_ID,
        review_note: (reviewNote[id] || '').trim() || null,
      })
      setReviewNote((prev) => ({ ...prev, [id]: '' }))
      if (onRefresh) onRefresh()
      // Reload the document list to show updated status
      getApplicationDocuments(applicationId)
        .then((list) => setRealDocs(list || []))
        .catch(() => {})
    } catch (e) {
      setDocErr((prev) => ({ ...prev, [id]: e.message }))
    } finally {
      setBusy((prev) => ({ ...prev, [id]: false }))
    }
  }

  // ── Render the real documents from application_documents collection ──

  if (!loadDone) {
    return <p className="drp__loading">Loading documents…</p>
  }

  if (loadErr) {
    return (
      <div>
        <div className="alert alert--error drp__load-err">{loadErr}</div>
        {/* Fall back to simple submitted/not-submitted list */}
        <div className="drp__list">
          {documents.map((doc) => (
            <div key={doc.name} className={`drp__row${doc.submitted ? ' drp__row--submitted' : ' drp__row--pending'}`}>
              <span className="drp__icon">{doc.submitted ? '✓' : '○'}</span>
              <span className="drp__name">{doc.name.replace(/_/g, ' ')}</span>
              <span className={`drp__badge${doc.submitted ? ' drp__badge--ok' : ' drp__badge--pending'}`}>
                {doc.submitted ? 'Submitted' : 'Not Submitted'}
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (realDocs.length === 0) {
    // No uploaded documents yet — show required list as not-submitted
    if (documents.length === 0) {
      return <p className="drp__empty">No required documents on record for this application.</p>
    }
    return (
      <div>
        <div className="drp__list">
          {documents.map((doc) => (
            <div key={doc.name} className="drp__row drp__row--pending">
              <span className="drp__icon">○</span>
              <span className="drp__name">{doc.name.replace(/_/g, ' ')}</span>
              <span className="drp__badge drp__badge--pending">Not Submitted</span>
            </div>
          ))}
        </div>
        <p className="drp__pending-note">
          No documents have been uploaded yet for this application.
        </p>
      </div>
    )
  }

  return (
    <div className="drp">
      <div className="drp__list">
        {realDocs.map((doc) => {
          const id   = doc.document_id
          const sb   = statusBadge(doc.status)
          const isBusy = busy[id]

          return (
            <div
              key={id}
              className={`drp__row${doc.status === 'verified' ? ' drp__row--submitted' : doc.status === 'rejected' ? ' drp__row--rejected' : ' drp__row--pending'}`}
            >
              <div className="drp__row-top">
                <span className="drp__icon">
                  {doc.status === 'verified' ? '✓' : doc.status === 'rejected' ? '✗' : '○'}
                </span>
                <div className="drp__info">
                  <span className="drp__name">{doc.document_type?.replace(/_/g, ' ') || doc.filename}</span>
                  <span className="drp__filename">{doc.filename}</span>
                  {doc.uploaded_at && (
                    <span className="drp__date">Uploaded {formatDate(doc.uploaded_at)}</span>
                  )}
                </div>
                <span className={`drp__badge ${sb.cls}`}>{sb.label}</span>

                {doc.status === 'pending_review' || doc.status === 'uploaded' ? (
                  <div className="drp__actions">
                    <button
                      className="drp__btn drp__btn--verify"
                      disabled={isBusy}
                      onClick={() => doReview(doc, 'verified')}
                    >
                      {isBusy ? '…' : 'Accept'}
                    </button>
                    <button
                      className="drp__btn drp__btn--reject"
                      disabled={isBusy}
                      onClick={() => doReview(doc, 'rejected')}
                    >
                      {isBusy ? '…' : 'Reject'}
                    </button>
                  </div>
                ) : (
                  <div className="drp__actions">
                    <button
                      className="drp__btn drp__btn--verify"
                      disabled={isBusy}
                      onClick={() => doReview(doc, 'verified')}
                    >
                      Re-verify
                    </button>
                    <button
                      className="drp__btn drp__btn--reject"
                      disabled={isBusy}
                      onClick={() => doReview(doc, 'rejected')}
                    >
                      Re-reject
                    </button>
                  </div>
                )}
              </div>

              {/* Review note input */}
              <div className="drp__note-row">
                <input
                  type="text"
                  className="form-input drp__note-input"
                  placeholder="Review note (optional)"
                  value={reviewNote[id] || ''}
                  onChange={(e) => setReviewNote((prev) => ({ ...prev, [id]: e.target.value }))}
                  disabled={isBusy}
                />
              </div>

              {doc.review_note && (
                <div className="drp__prev-note">
                  Previous note: <em>{doc.review_note}</em>
                  {doc.reviewed_by && ` — by ${doc.reviewed_by}`}
                </div>
              )}

              {docErr[id] && (
                <div className="alert alert--error drp__doc-err">{docErr[id]}</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
