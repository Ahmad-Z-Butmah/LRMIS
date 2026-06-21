import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import StaffLayout from '../../components/StaffLayout'
import StatusBadge from '../../components/StatusBadge'
import DocumentReviewPanel from '../../components/DocumentReviewPanel'
import SurveyMilestoneStepper from '../../components/SurveyMilestoneStepper'
import {
  getApplications,
  getApplicationById,
  transitionApplication,
  rejectApplication,
  markMissingDocuments,
} from '../../api/staffConsoleApi'
import { getSurveyorTasks, updateSurveyMilestone } from '../../api/surveyApi'
import './RegistrarReview.css'

const ACTOR_ID = 'staff_console'

// Standard legal document types the registrar must verify
const LEGAL_DOC_LABELS = {
  ownership_deed:   'Ownership Deed',
  sale_contract:    'Sale Contract',
  id_copy:          'ID Copy',
  survey_report:    'Survey Report',
  national_id:      'National ID',
  title_deed:       'Title Deed',
  power_of_attorney:'Power of Attorney',
}

function docLabel(name) {
  return LEGAL_DOC_LABELS[name] || name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

function parcelLabel(ref) {
  if (!ref) return '—'
  if (typeof ref === 'string') return ref
  return ref.parcel_number || '—'
}

function zoneLabel(ref) {
  if (!ref || typeof ref === 'string') return '—'
  return ref.zone_id || '—'
}

function allowed(app, state) {
  return (app?.workflow?.allowed_next || []).includes(state)
}

// ── Student 3: Survey Report Section ─────────────────────────────────────────
// Fetches the survey task for this application (via assignment.assigned_surveyor_id
// stored on the application document) and displays milestone history + action.
// Registrar can advance the task to 'registrar_reviewed' if it is at 'report_uploaded'.

const MILESTONE_LABELS_S3 = {
  assigned:           'Assigned',
  visit_scheduled:    'Visit Scheduled',
  arrived_on_site:    'Arrived on Site',
  survey_started:     'Survey Started',
  survey_completed:   'Survey Completed',
  report_uploaded:    'Report Uploaded',
  registrar_reviewed: 'Registrar Reviewed',
}

function SurveyReportSection({ appId, detail, onRefresh }) {
  const surveyorId  = detail?.assignment?.assigned_surveyor_id
  const [task,  setTask]    = useState(null)
  const [loading, setLoading] = useState(false)
  const [err,   setErr]     = useState(null)
  const [busy,  setBusy]    = useState(false)
  const [success, setSuccess] = useState(null)
  const [actionErr, setActionErr] = useState(null)
  const [reviewNote, setReviewNote] = useState('')

  useEffect(() => {
    if (!surveyorId) return
    setLoading(true)
    setErr(null)
    getSurveyorTasks(surveyorId)
      .then((data) => {
        const found = (data?.tasks || []).find((t) => t.application_id === appId)
        setTask(found || null)
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [surveyorId, appId])

  async function handleMarkReviewed() {
    if (!task || busy) return
    setBusy(true)
    setActionErr(null)
    setSuccess(null)
    try {
      await updateSurveyMilestone(appId, {
        milestone: 'registrar_reviewed',
        by: ACTOR_ID,
        note: reviewNote.trim() || undefined,
      })
      setSuccess('Survey task marked as Registrar Reviewed.')
      setReviewNote('')
      // Refresh task data
      getSurveyorTasks(surveyorId)
        .then((data) => {
          const found = (data?.tasks || []).find((t) => t.application_id === appId)
          setTask(found || null)
        })
        .catch(() => {})
      onRefresh()
    } catch (e) {
      setActionErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  // No surveyor assigned yet
  if (!surveyorId) {
    return (
      <div className="rr-detail__section">
        <h4 className="rr-detail__section-title">Survey Report</h4>
        <p className="rr-detail__empty">
          No surveyor is assigned to this application yet.
          Auto-assign a surveyor first via the Applications workflow.
        </p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="rr-detail__section">
        <h4 className="rr-detail__section-title">Survey Report</h4>
        <p className="rr-detail__empty">Loading survey task…</p>
      </div>
    )
  }

  if (err) {
    return (
      <div className="rr-detail__section">
        <h4 className="rr-detail__section-title">Survey Report</h4>
        <div className="alert alert--error" style={{ margin: 0 }}>
          Failed to load survey task: {err}
        </div>
      </div>
    )
  }

  if (!task) {
    return (
      <div className="rr-detail__section">
        <h4 className="rr-detail__section-title">Survey Report</h4>
        <p className="rr-detail__empty">
          No active survey task found for surveyor <code>{surveyorId}</code>.
        </p>
      </div>
    )
  }

  const canMarkReviewed = task.status === 'report_uploaded'
  const isAlreadyReviewed = task.status === 'registrar_reviewed'

  return (
    <div className="rr-detail__section">
      <h4 className="rr-detail__section-title">Survey Report</h4>

      {/* Task summary row */}
      <div className="rr-survey-summary">
        <div className="rr-survey-field">
          <span className="rr-survey-label">Task ID</span>
          <code className="rr-app-id">{task.task_id || '—'}</code>
        </div>
        <div className="rr-survey-field">
          <span className="rr-survey-label">Surveyor</span>
          <span>{surveyorId}</span>
        </div>
        <div className="rr-survey-field">
          <span className="rr-survey-label">Report Uploaded</span>
          <span className={task.report_uploaded ? 'rr-survey-yes' : 'rr-survey-no'}>
            {task.report_uploaded ? 'Yes' : 'No'}
          </span>
        </div>
      </div>

      {/* Milestone stepper */}
      <div style={{ marginTop: 14 }}>
        <SurveyMilestoneStepper
          currentMilestone={task.status || task.current_milestone || 'assigned'}
        />
      </div>

      {/* Milestone history (last 3) */}
      {task.milestones && task.milestones.length > 0 && (
        <div className="rr-survey-history">
          {[...task.milestones].reverse().slice(0, 3).map((m, i) => (
            <div key={i} className="rr-survey-history__entry">
              <span className="rr-survey-history__milestone">
                {MILESTONE_LABELS_S3[m.milestone] || m.milestone}
              </span>
              <span className="rr-survey-history__by">by {m.by || '—'}</span>
              {m.note && <span className="rr-survey-history__note">{m.note}</span>}
            </div>
          ))}
          {task.milestones.length > 3 && (
            <p className="rr-detail__empty" style={{ marginTop: 6 }}>
              +{task.milestones.length - 3} earlier entries…
            </p>
          )}
        </div>
      )}

      {/* Registrar action */}
      {isAlreadyReviewed && (
        <div className="rr-detail__success" style={{ marginTop: 12 }}>
          Survey report has been reviewed by the registrar.
        </div>
      )}

      {!isAlreadyReviewed && !canMarkReviewed && (
        <p className="rr-detail__empty" style={{ marginTop: 12 }}>
          Survey report review is available once the task reaches{' '}
          <strong>Report Uploaded</strong> milestone
          (current: <strong>{MILESTONE_LABELS_S3[task.status] || task.status}</strong>).
        </p>
      )}

      {canMarkReviewed && (
        <div className="rr-survey-action">
          <div className="form-field" style={{ marginBottom: 10 }}>
            <label className="form-label">Decision Note (optional — saved with accept action)</label>
            <textarea
              className="form-input"
              rows={2}
              placeholder="Add registrar review notes for the survey report…"
              value={reviewNote}
              onChange={(e) => setReviewNote(e.target.value)}
              disabled={busy}
            />
          </div>
          {actionErr && (
            <div className="alert alert--error" style={{ marginBottom: 8 }}>
              {actionErr}
            </div>
          )}
          {success && (
            <div className="rr-detail__success" style={{ marginBottom: 8 }}>
              {success}
            </div>
          )}
          <div className="rr-survey-decision-row">
            <button
              type="button"
              className="rr-btn rr-btn--approve"
              disabled={busy}
              onClick={handleMarkReviewed}
            >
              {busy ? 'Saving…' : 'Accept Survey Report'}
            </button>

            {/* Reject is disabled — backend has no reject-survey milestone */}
            <button
              type="button"
              className="rr-btn rr-btn--danger"
              disabled
              title="Backend has no reject-survey-report mechanism. See limitation note below."
            >
              Reject Survey Report
            </button>
          </div>

          <div className="rr-survey-limit-note">
            <strong>Limitation:</strong> The backend has no <em>reject survey report</em> mechanism.
            The survey milestone sequence only advances forward (no reversal or rejection step).
            To document a rejection: add a decision note above and use the application-level
            Reject action in the Registrar Decision section, or request a new survey via
            the application workflow.
            A dedicated <code>registrar-review</code> endpoint is not yet implemented
            (<code>registrar</code> router is a placeholder).
          </div>
        </div>
      )}

      {/* Limitation notice */}
      <p className="rr-detail__objection-note" style={{ marginTop: 10 }}>
        Note: Dedicated survey report file upload endpoint not yet available
        (<code>survey_reports</code> router is a placeholder).
        Milestone advancement uses <code>PATCH /applications/&#123;id&#125;/survey-milestone</code>.
      </p>
    </div>
  )
}

// ── Detail panel shown inline below a selected row ─────────────────────────

function ReviewDetail({ appId, listApp, onRefresh }) {
  const navigate = useNavigate()
  const [detail, setDetail]       = useState(null)
  const [loadErr, setLoadErr]     = useState(null)
  const [loading, setLoading]     = useState(true)
  const [busy,    setBusy]        = useState(false)
  const [actionErr, setActionErr] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  // Decision notes (sent as `note` with transition/reject)
  const [decisionNote, setDecisionNote] = useState('')

  // Reject modal inline state
  const [rejectReason, setRejectReason] = useState('')
  const [missingInput, setMissingInput] = useState('')
  const [confirmMode,  setConfirmMode]  = useState(null) // 'reject' | 'missing' | null

  useEffect(() => {
    setLoading(true)
    setLoadErr(null)
    getApplicationById(appId)
      .then(setDetail)
      .catch((e) => setLoadErr(e.message))
      .finally(() => setLoading(false))
  }, [appId])

  if (loading) return <div className="rr-detail__loading">Loading application detail…</div>
  if (loadErr)  return <div className="rr-detail__err">Failed to load detail: {loadErr}</div>
  if (!detail)  return null

  const objectionStatus = detail.objection_status
  const notes           = detail.internal_notes || []

  // Transition wrapper — also passes decision note if provided
  async function doTransition(targetState) {
    setBusy(true)
    setActionErr(null)
    setSuccessMsg(null)
    try {
      await transitionApplication(appId, {
        target_state: targetState,
        actor_type:   'staff',
        actor_id:     ACTOR_ID,
        note:         decisionNote.trim() || undefined,
      })
      setSuccessMsg(`Application transitioned to "${targetState}".`)
      setDecisionNote('')
      onRefresh()
    } catch (e) {
      setActionErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function doReject(e) {
    e.preventDefault()
    if (!rejectReason.trim()) return
    setBusy(true)
    setActionErr(null)
    setSuccessMsg(null)
    try {
      await rejectApplication(appId, {
        reason:      rejectReason.trim(),
        rejected_by: ACTOR_ID,
      })
      setSuccessMsg('Application rejected.')
      setRejectReason('')
      setConfirmMode(null)
      onRefresh()
    } catch (e) {
      setActionErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function doMissingDocs(e) {
    e.preventDefault()
    const docList = missingInput.split(',').map((d) => d.trim()).filter(Boolean)
    if (!docList.length) return
    setBusy(true)
    setActionErr(null)
    setSuccessMsg(null)
    try {
      await markMissingDocuments(appId, { missing_documents: docList })
      setSuccessMsg('Missing document request sent.')
      setMissingInput('')
      setConfirmMode(null)
      onRefresh()
    } catch (e) {
      setActionErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rr-detail">

      {/* ── Section 1: Legal Documents — Accept / Reject via DocumentReviewPanel ── */}
      <div className="rr-detail__section">
        <h4 className="rr-detail__section-title">Legal Document Checklist</h4>
        <DocumentReviewPanel
          applicationId={appId}
          documents={detail.documents || []}
          onRefresh={onRefresh}
        />
      </div>

      {/* ── Section 2: Objections ── */}
      <div className="rr-detail__section">
        <h4 className="rr-detail__section-title">Objections</h4>
        {objectionStatus ? (
          <div className="rr-detail__objection">
            <span className="rr-detail__objection-label">Objection status:</span>
            <span className="rr-detail__objection-status">{objectionStatus}</span>
            <p className="rr-detail__objection-note">
              Full objection details (text, submitter) require a
              <code> GET /applications/&#123;id&#125;/objections</code> endpoint.
              Only the status field is returned by the current detail endpoint.
            </p>
          </div>
        ) : (
          <p className="rr-detail__empty">No objection on record for this application.</p>
        )}
      </div>

      {/* ── Section 3: Internal Notes ── */}
      {notes.length > 0 && (
        <div className="rr-detail__section">
          <h4 className="rr-detail__section-title">Registrar / Staff Notes</h4>
          <div className="rr-detail__notes">
            {notes.map((n, i) => (
              <div key={i} className="rr-detail__note">
                <span className="rr-detail__note-author">{n.actor_id || n.author || 'staff'}</span>
                <span className="rr-detail__note-time">
                  {n.timestamp || n.created_at
                    ? new Date(n.timestamp || n.created_at).toLocaleString('en-GB')
                    : '—'}
                </span>
                <p className="rr-detail__note-text">{n.text || n.content || n.note || '—'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Section 3b: Survey Report (Student 3) ── */}
      <SurveyReportSection
        appId={appId}
        detail={detail}
        onRefresh={onRefresh}
      />

      {/* ── Section 4: Registrar Decision ── */}
      <div className="rr-detail__section">
        <h4 className="rr-detail__section-title">Registrar Decision</h4>

        <div className="form-field">
          <label className="form-label">Decision Notes (optional — saved with the action)</label>
          <textarea
            className="form-input"
            rows={2}
            value={decisionNote}
            onChange={(e) => setDecisionNote(e.target.value)}
            placeholder="Add registrar notes to accompany this decision…"
            disabled={busy}
          />
        </div>

        {actionErr  && <div className="alert alert--error rr-detail__err-msg">{actionErr}</div>}
        {successMsg && <div className="rr-detail__success">{successMsg}</div>}

        <div className="rr-detail__actions">

          {allowed(listApp, 'approved') && confirmMode !== 'reject' && confirmMode !== 'missing' && (
            <button
              className="rr-btn rr-btn--approve"
              disabled={busy}
              onClick={() => doTransition('approved')}
            >
              {busy ? 'Working…' : 'Approve Application'}
            </button>
          )}

          {allowed(listApp, 'under_objection') && confirmMode === null && (
            <button
              className="rr-btn rr-btn--objection"
              disabled={busy}
              onClick={() => doTransition('under_objection')}
            >
              {busy ? 'Working…' : 'Move to Under Objection'}
            </button>
          )}

          {allowed(listApp, 'missing_documents') && confirmMode === null && (
            <button
              className="rr-btn rr-btn--warn"
              onClick={() => setConfirmMode('missing')}
            >
              Request Missing Docs
            </button>
          )}

          {allowed(listApp, 'rejected') && confirmMode === null && (
            <button
              className="rr-btn rr-btn--danger"
              onClick={() => setConfirmMode('reject')}
            >
              Reject Application
            </button>
          )}
        </div>

        {/* ── Reject inline form ── */}
        {confirmMode === 'reject' && (
          <form className="rr-detail__inline-form" onSubmit={doReject}>
            <label className="form-label">
              Rejection reason <span className="rr-required">*</span>
            </label>
            <textarea
              className="form-input"
              rows={2}
              required
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="State grounds for rejection…"
            />
            <div className="rr-detail__inline-footer">
              <button type="button" className="btn btn--muted" onClick={() => setConfirmMode(null)}>
                Cancel
              </button>
              <button type="submit" className="btn btn--danger" disabled={busy}>
                {busy ? 'Rejecting…' : 'Confirm Reject'}
              </button>
            </div>
          </form>
        )}

        {/* ── Missing docs inline form ── */}
        {confirmMode === 'missing' && (
          <form className="rr-detail__inline-form" onSubmit={doMissingDocs}>
            <label className="form-label">
              Missing document names (comma-separated) <span className="rr-required">*</span>
            </label>
            <input
              type="text"
              className="form-input"
              required
              value={missingInput}
              onChange={(e) => setMissingInput(e.target.value)}
              placeholder="ownership_deed, survey_report"
            />
            <div className="rr-detail__inline-footer">
              <button type="button" className="btn btn--muted" onClick={() => setConfirmMode(null)}>
                Cancel
              </button>
              <button type="submit" className="btn btn--warning" disabled={busy}>
                {busy ? 'Sending…' : 'Send Request'}
              </button>
            </div>
          </form>
        )}

        <div className="rr-detail__view-link">
          <button
            className="rr-btn rr-btn--view"
            onClick={() => navigate(`/staff/applications/${appId}`)}
          >
            Open Full Application Details →
          </button>
        </div>
      </div>

    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function RegistrarReview() {
  const navigate = useNavigate()
  const { applicationId: paramId } = useParams()

  const [apps, setApps]             = useState([])
  const [loading, setLoading]       = useState(true)
  const [pageError, setPageError]   = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const [autoExpanded, setAutoExpanded] = useState(false)

  // Auto-expand the row whose ID came from the URL param (runs once after first load)
  useEffect(() => {
    if (!autoExpanded && paramId && apps.length > 0) {
      setExpandedId(paramId)
      setAutoExpanded(true)
    }
  }, [apps, paramId, autoExpanded])

  const loadApps = useCallback(() => {
    setLoading(true)
    setPageError(null)
    setExpandedId(null)
    async function fetchAll() {
      const first = await getApplications({ status: 'legal_review', limit: 100, page: 1 })
      const items = [...(first.items || [])]
      const totalPages = first.total > 0 ? Math.ceil(first.total / 100) : 1
      if (totalPages > 1) {
        const extras = await Promise.all(
          Array.from({ length: totalPages - 1 }, (_, i) =>
            getApplications({ status: 'legal_review', limit: 100, page: i + 2 })
          )
        )
        extras.forEach((r) => items.push(...(r.items || [])))
      }
      return items
    }
    fetchAll()
      .then((items) => setApps(items))
      .catch((e) => setPageError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadApps() }, [loadApps])

  const toggleExpand = (id) => setExpandedId((prev) => (prev === id ? null : id))

  return (
    <StaffLayout>
      <div className="page-container">

        <div className="rr-page-header">
          <div>
            <h1 className="rr-page-header__title">Registrar Review</h1>
            <p className="rr-page-header__desc">
              {loading
                ? 'Loading…'
                : `${apps.length} application${apps.length !== 1 ? 's' : ''} awaiting legal review`}
            </p>
          </div>
          <button className="btn btn--outline" onClick={() => navigate('/staff/dashboard')}>
            ← Dashboard
          </button>
        </div>

        {pageError && <div className="alert alert--error">{pageError}</div>}

        <div className="rr-help-card card">
          <p className="rr-help-text">
            Click <strong>Review</strong> on any row to expand the registrar review panel for that
            application. The panel shows the legal document checklist, objection status, decision
            notes, and decision actions. All action buttons appear only when the backend workflow
            engine permits the transition.
          </p>
        </div>

        <div className="card rr-table-card">
          {loading && (
            <div className="rr-loading">Loading applications in legal review…</div>
          )}

          {!loading && apps.length === 0 && !pageError && (
            <div className="rr-empty">
              <div className="rr-empty__icon">⚖</div>
              <p>No applications are currently awaiting legal review.</p>
            </div>
          )}

          {!loading && apps.length > 0 && (
            <div className="rr-table-scroll">
              <table className="rr-table">
                <thead>
                  <tr>
                    <th></th>
                    <th>Application ID</th>
                    <th>Applicant</th>
                    <th>Type</th>
                    <th>Parcel / Zone</th>
                    <th>Required Documents</th>
                    <th>Submitted</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {apps.map((app) => (
                    <React.Fragment key={app.application_id}>
                      <tr className={expandedId === app.application_id ? 'rr-tr--expanded' : ''}>
                        <td>
                          <button
                            className={`rr-btn rr-btn--review${expandedId === app.application_id ? ' rr-btn--active' : ''}`}
                            onClick={() => toggleExpand(app.application_id)}
                          >
                            {expandedId === app.application_id ? 'Close ▲' : 'Review ▼'}
                          </button>
                        </td>
                        <td>
                          <code className="rr-app-id">{app.application_id}</code>
                        </td>
                        <td className="rr-td-muted">{app.applicant_ref || '—'}</td>
                        <td className="rr-td-muted">
                          {app.application_type?.replace(/_/g, ' ') || '—'}
                        </td>
                        <td className="rr-td-muted">
                          {parcelLabel(app.parcel_ref)}
                          {zoneLabel(app.parcel_ref) !== '—' && (
                            <span className="rr-zone"> / {zoneLabel(app.parcel_ref)}</span>
                          )}
                        </td>
                        <td className="rr-td-docs">
                          {(app.required_documents || []).length > 0
                            ? (app.required_documents || []).map(docLabel).join(', ')
                            : '—'}
                        </td>
                        <td className="rr-td-muted">
                          {formatDate(app.submitted_at || app.created_at)}
                        </td>
                        <td>
                          <StatusBadge status={app.status} />
                        </td>
                      </tr>

                      {/* ── Expandable detail row ── */}
                      {expandedId === app.application_id && (
                        <tr className="rr-tr--detail">
                          <td colSpan={8} className="rr-td--detail">
                            <ReviewDetail
                              appId={app.application_id}
                              listApp={app}
                              onRefresh={loadApps}
                            />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </StaffLayout>
  )
}
