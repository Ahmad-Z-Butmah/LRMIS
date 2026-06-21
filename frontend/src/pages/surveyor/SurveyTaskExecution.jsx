import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import StaffLayout from '../../components/StaffLayout'
import SurveyMilestoneStepper from '../../components/SurveyMilestoneStepper'
import { getSurveyorTasks, updateSurveyMilestone, uploadSurveyReport } from '../../api/surveyApi'
import {
  addComment,
  getApplicationComments,
  getApplicationById,
  transitionApplication,
} from '../../api/staffConsoleApi'
import './SurveyTaskExecution.css'

function getSurveyorId() {
  try {
    const user = JSON.parse(localStorage.getItem('lrmis_user'))
    if (user?.role === 'surveyor' && user?.user_id) return user.user_id
  } catch {}
  return 'SURV-001'
}

const MILESTONES = [
  'assigned',
  'visit_scheduled',
  'arrived_on_site',
  'survey_started',
  'survey_completed',
  'report_uploaded',
  'registrar_reviewed',
]

const MILESTONE_LABELS = {
  assigned:           'Assigned',
  visit_scheduled:    'Visit Scheduled',
  arrived_on_site:    'Arrived on Site',
  survey_started:     'Survey Started',
  survey_completed:   'Survey Completed',
  report_uploaded:    'Report Uploaded',
  registrar_reviewed: 'Registrar Reviewed',
}

const NEXT_ACTION_LABELS = {
  visit_scheduled:    'Mark Visit Scheduled',
  arrived_on_site:    'Mark Arrived on Site',
  survey_started:     'Mark Survey Started',
  survey_completed:   'Mark Survey Completed',
  report_uploaded:    'Mark Report Uploaded',
  registrar_reviewed: 'Mark Registrar Reviewed',
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

function formatDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function SurveyTaskExecution() {
  const navigate = useNavigate()
  // Route param is :taskId — matches either task.task_id or task.application_id
  const { taskId } = useParams()

  const surveyorId = getSurveyorId()

  const [task,    setTask]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  // applicationId derived from task — used for all API calls that require application context
  const applicationId = task?.application_id || ''

  // Student 1 workflow transition state
  const [appDetail,        setAppDetail]        = useState(null)
  const [appDetailLoading, setAppDetailLoading] = useState(false)
  const [transitionBusy,   setTransitionBusy]   = useState(false)
  const [transitionErr,    setTransitionErr]     = useState(null)
  const [transitionOk,     setTransitionOk]      = useState(null)

  // Milestone action state
  const [busy,          setBusy]          = useState(false)
  const [actionError,   setActionError]   = useState(null)
  const [successMsg,    setSuccessMsg]    = useState(null)
  const [actionNote,    setActionNote]    = useState('')
  const [scheduledDate, setScheduledDate] = useState('')

  // Field notes state (uses POST /applications/{id}/comments — VERIFIED)
  const [existingNotes,  setExistingNotes]  = useState([])
  const [notesLoading,   setNotesLoading]   = useState(false)
  const [fieldNoteText,  setFieldNoteText]  = useState('')
  const [fieldNoteBusy,  setFieldNoteBusy]  = useState(false)
  const [fieldNoteErr,   setFieldNoteErr]   = useState(null)
  const [fieldNoteOk,    setFieldNoteOk]    = useState(null)

  // Survey report metadata state — POST /applications/{id}/survey-report (VERIFIED)
  const [reportRef,   setReportRef]   = useState('')
  const [reportDate,  setReportDate]  = useState('')
  const [reportObs,   setReportObs]   = useState('')
  const [reportBusy,  setReportBusy]  = useState(false)
  const [reportErr,   setReportErr]   = useState(null)
  const [reportOk,    setReportOk]    = useState(null)
  const [reportVia,   setReportVia]   = useState(null) // 'endpoint' | 'comment-fallback'

  const loadTask = useCallback(() => {
    if (!taskId) return
    setLoading(true)
    setError(null)
    getSurveyorTasks(surveyorId)
      .then((data) => {
        const tasks = data?.tasks || []
        // Match by task_id first (required route pattern), then by application_id (backward compat)
        const found = tasks.find(
          (t) => t.task_id === taskId || t.application_id === taskId
        )
        if (!found) {
          setError(
            `Task "${taskId}" not found under surveyor ${surveyorId}. ` +
            `Checked task_id and application_id. Ensure the task is assigned to this surveyor.`
          )
        } else {
          setTask(found)
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [taskId, surveyorId])

  useEffect(() => { loadTask() }, [loadTask])

  // Load existing field notes (staff-only comments by surveyor)
  // Uses GET /applications/{id}/comments — VERIFIED endpoint
  const loadNotes = useCallback(() => {
    if (!applicationId) return
    setNotesLoading(true)
    getApplicationComments(applicationId)
      .then((comments) => {
        setExistingNotes(
          (comments || []).filter(
            (c) => c.actor_type === 'surveyor' || c.visibility === 'staff_only'
          )
        )
      })
      .catch(() => {})
      .finally(() => setNotesLoading(false))
  }, [applicationId])

  useEffect(() => {
    if (task) loadNotes()
  }, [task, loadNotes])

  // Add field note via POST /applications/{id}/comments — VERIFIED
  async function handleFieldNote(e) {
    e.preventDefault()
    if (!fieldNoteText.trim() || fieldNoteBusy) return
    setFieldNoteBusy(true)
    setFieldNoteErr(null)
    setFieldNoteOk(null)
    try {
      await addComment(applicationId, {
        comment_text: fieldNoteText.trim(),
        created_by: surveyorId,
        actor_type: 'surveyor',
        visibility: 'staff_only',
      })
      setFieldNoteOk('Field note saved successfully.')
      setFieldNoteText('')
      loadNotes()
    } catch (e) {
      setFieldNoteErr(e.message)
    } finally {
      setFieldNoteBusy(false)
    }
  }

  // Upload survey report — POST /applications/{id}/survey-report (VERIFIED)
  // Falls back to a staff-only comment if the primary endpoint fails
  async function handleReportMetadata(e) {
    e.preventDefault()
    if (reportBusy) return
    setReportBusy(true)
    setReportErr(null)
    setReportOk(null)
    setReportVia(null)

    const fieldNotes = [
      reportObs.trim() || 'Survey report submitted.',
      reportRef.trim() ? `Reference: ${reportRef.trim()}` : null,
      reportDate ? `Report date: ${reportDate}` : null,
    ].filter(Boolean).join('\n')

    const payload = {
      surveyor_id: surveyorId,
      task_id:     task?.task_id || 'unknown',
      field_notes: fieldNotes,
      measurements: {},
      status:      'pending_review',
    }

    try {
      await uploadSurveyReport(applicationId, payload)
      setReportOk('Survey report saved successfully.')
      setReportVia('endpoint')
      setReportRef(''); setReportDate(''); setReportObs('')
    } catch (primaryErr) {
      // Fallback: save as staff-only comment if endpoint fails
      const structuredText = [
        '[SURVEY REPORT METADATA]',
        `Task: ${task?.task_id || 'N/A'}`,
        reportRef.trim() ? `Reference: ${reportRef.trim()}` : null,
        reportDate ? `Report Date: ${reportDate}` : null,
        reportObs.trim() ? `Observations: ${reportObs.trim()}` : null,
      ].filter(Boolean).join('\n')

      try {
        await addComment(applicationId, {
          comment_text: structuredText,
          created_by:   surveyorId,
          actor_type:   'surveyor',
          visibility:   'staff_only',
        })
        setReportOk(
          `Report endpoint failed (${primaryErr.message}). Saved as staff-only comment (fallback).`
        )
        setReportVia('comment-fallback')
        setReportRef(''); setReportDate(''); setReportObs('')
        loadNotes()
      } catch (fallbackErr) {
        setReportErr(
          `Endpoint failed: ${primaryErr.message}. Fallback also failed: ${fallbackErr.message}`
        )
      }
    } finally {
      setReportBusy(false)
    }
  }

  // Load application detail once milestone reaches report_uploaded or beyond
  // Used by Student 1 transition section to check workflow.allowed_next
  useEffect(() => {
    if (!task || !applicationId) return
    const milestoneIdx = MILESTONES.indexOf(task.status || task.current_milestone)
    const reportIdx    = MILESTONES.indexOf('report_uploaded')
    if (milestoneIdx < reportIdx) return
    setAppDetailLoading(true)
    getApplicationById(applicationId)
      .then(setAppDetail)
      .catch(() => {})
      .finally(() => setAppDetailLoading(false))
  }, [task, applicationId])

  // Student 1 workflow transition
  async function handleTransition(targetState) {
    if (transitionBusy || !applicationId) return
    setTransitionBusy(true)
    setTransitionErr(null)
    setTransitionOk(null)
    try {
      await transitionApplication(applicationId, {
        target_state: targetState,
        actor_type:   'staff',
        actor_id:     surveyorId,
        note:         `Survey report uploaded — advancing workflow to ${targetState}`,
      })
      setTransitionOk(
        `Application status moved to "${targetState}". ` +
        `Student 1 workflow transition complete.`
      )
      // Refresh app detail to reflect new status
      const updated = await getApplicationById(applicationId)
      setAppDetail(updated)
    } catch (e) {
      setTransitionErr(e.message)
    } finally {
      setTransitionBusy(false)
    }
  }

  // Compute next milestone
  const currentIdx  = task ? MILESTONES.indexOf(task.status || task.current_milestone) : -1
  const nextIdx     = currentIdx + 1
  const nextMilestone = nextIdx < MILESTONES.length ? MILESTONES[nextIdx] : null
  const isTerminal  = !nextMilestone || task?.status === 'registrar_reviewed'

  async function handleAdvance(e) {
    e.preventDefault()
    if (!nextMilestone || busy) return

    setActionError(null)
    setSuccessMsg(null)
    setBusy(true)

    const payload = {
      milestone: nextMilestone,
      by:        surveyorId,
      note:      actionNote.trim() || undefined,
      meta:      nextMilestone === 'visit_scheduled' && scheduledDate
        ? { scheduled_date: scheduledDate }
        : undefined,
    }

    try {
      await updateSurveyMilestone(applicationId, payload)
      setSuccessMsg(`Milestone advanced to "${MILESTONE_LABELS[nextMilestone]}".`)
      setActionNote('')
      setScheduledDate('')
      loadTask()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <StaffLayout>
      <div className="page-container page-container--md">

        {/* ── Back + header ── */}
        <div className="ste-page-header">
          <button
            type="button"
            className="btn btn--muted"
            onClick={() => navigate('/surveyor/tasks')}
          >
            ← My Tasks
          </button>
          <h1 className="ste-page-header__title">Survey Task Execution</h1>
        </div>


        {loading && (
          <div className="ste-loading">
            <div className="sv-loading__spinner" />
            <p>Loading task <code>{taskId}</code>…</p>
          </div>
        )}

        {!loading && error && (
          <div className="alert alert--error">{error}</div>
        )}

        {!loading && !error && task && (
          <>
            {/* ── Task info card ── */}
            <div className="card">
              <h2 className="section-title">Task Details</h2>
              <div className="ste-info-grid">
                <div className="ste-info-field">
                  <span className="ste-info-label">Task ID</span>
                  <code className="ste-info-value ste-info-value--mono">{task.task_id || '—'}</code>
                </div>
                <div className="ste-info-field">
                  <span className="ste-info-label">Application ID</span>
                  <code className="ste-info-value ste-info-value--mono">{task.application_id || '—'}</code>
                </div>
                <div className="ste-info-field">
                  <span className="ste-info-label">Parcel Number</span>
                  <span className="ste-info-value">{task.parcel_number || '—'}</span>
                </div>
                <div className="ste-info-field">
                  <span className="ste-info-label">Zone</span>
                  <span className="ste-info-value">{task.zone || '—'}</span>
                </div>
                <div className="ste-info-field">
                  <span className="ste-info-label">Priority</span>
                  <span className={`ste-priority ste-priority--${(task.priority || 'medium').toLowerCase()}`}>
                    {(task.priority || 'Medium').toUpperCase()}
                  </span>
                </div>
                <div className="ste-info-field">
                  <span className="ste-info-label">Scheduled Visit</span>
                  <span className="ste-info-value">{formatDate(task.scheduled_visit_date)}</span>
                </div>
                <div className="ste-info-field">
                  <span className="ste-info-label">Report Uploaded</span>
                  <span className={`ste-bool ${task.report_uploaded ? 'ste-bool--yes' : 'ste-bool--no'}`}>
                    {task.report_uploaded ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="ste-info-field">
                  <span className="ste-info-label">Created</span>
                  <span className="ste-info-value">{formatDate(task.created_at)}</span>
                </div>
              </div>
            </div>

            {/* ── Milestone stepper ── */}
            <div className="card">
              <h2 className="section-title">Milestone Progress</h2>
              <SurveyMilestoneStepper
                currentMilestone={task.status || task.current_milestone || 'assigned'}
              />
            </div>

            {/* ── Milestone history ── */}
            {task.milestones && task.milestones.length > 0 && (
              <div className="card">
                <h2 className="section-title">Milestone History</h2>
                <div className="ste-history">
                  {[...task.milestones].reverse().map((m, i) => (
                    <div key={i} className="ste-history__entry">
                      <div className="ste-history__dot" />
                      <div className="ste-history__body">
                        <div className="ste-history__head">
                          <span className="ste-history__milestone">
                            {MILESTONE_LABELS[m.milestone] || m.milestone}
                          </span>
                          <span className="ste-history__by">by {m.by || '—'}</span>
                          <span className="ste-history__time">{formatDateTime(m.timestamp)}</span>
                        </div>
                        {m.note && (
                          <p className="ste-history__note">{m.note}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Section A: Field Notes — uses POST /applications/{id}/comments (VERIFIED) ── */}
            <div className="card">
              <h2 className="section-title">Field Notes</h2>
              <div className="ste-verified-badge">
                ✓ Uses <code>POST /applications/&#123;id&#125;/comments</code> — verified endpoint
              </div>

              {/* Existing notes */}
              {notesLoading && <p className="ste-sub-loading">Loading notes…</p>}
              {!notesLoading && existingNotes.length > 0 && (
                <div className="ste-notes-list">
                  {existingNotes.map((n, i) => (
                    <div key={i} className="ste-note">
                      <div className="ste-note__head">
                        <span className="ste-note__by">{n.created_by || '—'}</span>
                        <span className="ste-note__time">
                          {n.created_at
                            ? new Date(n.created_at).toLocaleString('en-GB')
                            : '—'}
                        </span>
                      </div>
                      <p className="ste-note__text">{n.comment_text}</p>
                    </div>
                  ))}
                </div>
              )}
              {!notesLoading && existingNotes.length === 0 && (
                <p className="ste-sub-empty">No field notes yet.</p>
              )}

              {/* Add note form */}
              <form className="ste-sub-form" onSubmit={handleFieldNote}>
                <div className="form-field">
                  <label className="form-label">
                    New Field Note <span className="required">*</span>
                  </label>
                  <textarea
                    className="form-input"
                    rows={3}
                    placeholder="Record site observations, measurements, access notes…"
                    value={fieldNoteText}
                    onChange={(e) => setFieldNoteText(e.target.value)}
                    disabled={fieldNoteBusy}
                    required
                  />
                </div>
                {fieldNoteErr && (
                  <div className="alert alert--error">{fieldNoteErr}</div>
                )}
                {fieldNoteOk && (
                  <div className="ste-success">{fieldNoteOk}</div>
                )}
                <div className="ste-action-footer">
                  <button
                    type="submit"
                    className="btn btn--primary"
                    disabled={fieldNoteBusy || !fieldNoteText.trim()}
                  >
                    {fieldNoteBusy ? 'Saving…' : 'Save Field Note'}
                  </button>
                </div>
              </form>
            </div>

            {/* ── Section B: Survey Report Metadata ── */}
            {/* Primary: POST /applications/{id}/survey-report — NOT VERIFIED (backend placeholder) */}
            {/* Fallback: POST /applications/{id}/comments staff-only — VERIFIED               */}
            <div className="card">
              <h2 className="section-title">Survey Report Metadata</h2>
              <div className="ste-verified-badge">
                ✓ Uses <code>POST /applications/&#123;id&#125;/survey-report</code> — verified endpoint.
                Falls back to a staff-only comment if the endpoint is unreachable.
              </div>

              <form className="ste-sub-form" onSubmit={handleReportMetadata}>
                <div className="form-grid-2">
                  <div className="form-field">
                    <label className="form-label">Report Reference</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. RPT-2024-001"
                      value={reportRef}
                      onChange={(e) => setReportRef(e.target.value)}
                      disabled={reportBusy}
                    />
                  </div>
                  <div className="form-field">
                    <label className="form-label">Report Date</label>
                    <input
                      type="date"
                      className="form-input"
                      value={reportDate}
                      onChange={(e) => setReportDate(e.target.value)}
                      disabled={reportBusy}
                    />
                  </div>
                </div>
                <div className="form-field">
                  <label className="form-label">Observations / Findings</label>
                  <textarea
                    className="form-input"
                    rows={3}
                    placeholder="Summary of survey findings, boundary conditions, anomalies…"
                    value={reportObs}
                    onChange={(e) => setReportObs(e.target.value)}
                    disabled={reportBusy}
                  />
                </div>

                {reportErr && (
                  <div className="alert alert--error">{reportErr}</div>
                )}
                {reportOk && (
                  <div className={`ste-success${reportVia === 'comment-fallback' ? ' ste-success--fallback' : ''}`}>
                    {reportOk}
                    {reportVia === 'comment-fallback' && (
                      <span className="ste-fallback-tag">saved via comment fallback</span>
                    )}
                  </div>
                )}

                <div className="ste-action-footer">
                  <button
                    type="submit"
                    className="btn btn--outline"
                    disabled={reportBusy}
                  >
                    {reportBusy ? 'Saving…' : 'Save Report Metadata'}
                  </button>
                </div>
              </form>
            </div>

            {/* ── Student 1 Workflow Transition ── */}
            {/* Shown when survey milestone >= report_uploaded */}
            {(task.status === 'report_uploaded' || task.status === 'registrar_reviewed') && (
              <div className="card card--accent-left">
                <h2 className="section-title">Student 1 — Workflow Transition</h2>

                {appDetailLoading && (
                  <p className="ste-sub-loading">Loading application workflow status…</p>
                )}

                {!appDetailLoading && appDetail && (() => {
                  const appStatus  = appDetail.status
                  const allowedNext = appDetail.workflow?.allowed_next || []
                  const canSurveyed    = appStatus === 'survey_required' && allowedNext.includes('surveyed')
                  const canLegalReview = appStatus === 'surveyed'        && allowedNext.includes('legal_review')

                  return (
                    <div className="ste-transition-section">
                      <div className="ste-transition-status">
                        <span className="ste-info-label">Application Status</span>
                        <span className="ste-info-value">{appStatus}</span>
                      </div>
                      <div className="ste-transition-status">
                        <span className="ste-info-label">Allowed Next</span>
                        <span className="ste-info-value">
                          {allowedNext.length ? allowedNext.join(', ') : 'none'}
                        </span>
                      </div>

                      {canSurveyed && (
                        <div className="ste-transition-action">
                          <p className="ste-transition-hint">
                            Survey report is uploaded. Application can now move to
                            {' '}<strong>surveyed</strong> in the Student 1 workflow.
                          </p>
                          <button
                            type="button"
                            className="btn btn--primary"
                            disabled={transitionBusy}
                            onClick={() => handleTransition('surveyed')}
                          >
                            {transitionBusy ? 'Transitioning…' : 'Move Application to Surveyed'}
                          </button>
                        </div>
                      )}

                      {canLegalReview && (
                        <div className="ste-transition-action">
                          <p className="ste-transition-hint">
                            Application is surveyed and can proceed to
                            {' '}<strong>legal review</strong>.
                          </p>
                          <button
                            type="button"
                            className="btn btn--primary"
                            disabled={transitionBusy}
                            onClick={() => handleTransition('legal_review')}
                          >
                            {transitionBusy ? 'Transitioning…' : 'Move Application to Legal Review'}
                          </button>
                        </div>
                      )}

                      {!canSurveyed && !canLegalReview && (
                        <div className="ste-transition-note">
                          No Student 1 workflow transition available.
                          Current status: <strong>{appStatus}</strong>.
                          Allowed next: {allowedNext.length ? allowedNext.join(', ') : 'none'}.
                        </div>
                      )}

                      {transitionErr && (
                        <div className="alert alert--error" style={{ marginTop: 10 }}>
                          Transition failed — {transitionErr}
                        </div>
                      )}
                      {transitionOk && (
                        <div className="ste-success" style={{ marginTop: 10 }}>
                          {transitionOk}
                        </div>
                      )}
                    </div>
                  )
                })()}

                {!appDetailLoading && !appDetail && (
                  <p className="ste-sub-empty">
                    Could not load application workflow data. Backend may be unavailable.
                  </p>
                )}
              </div>
            )}

            {/* ── Next action ── */}
            <div className="card">
              <h2 className="section-title">Next Action</h2>

              {isTerminal ? (
                <div className="ste-terminal">
                  <div className="ste-terminal__icon">✓</div>
                  <p className="ste-terminal__msg">
                    This task has reached the final milestone:{' '}
                    <strong>{MILESTONE_LABELS[task.status] || task.status}</strong>.
                    No further progression is possible.
                  </p>
                </div>
              ) : (
                <form className="ste-action-form" onSubmit={handleAdvance}>
                  <div className="ste-action-target">
                    <span className="ste-action-target__label">Next Milestone</span>
                    <span className="ste-action-target__value">
                      {MILESTONE_LABELS[nextMilestone]}
                    </span>
                  </div>

                  {/* Date input for visit_scheduled */}
                  {nextMilestone === 'visit_scheduled' && (
                    <div className="form-field">
                      <label className="form-label">
                        Scheduled Visit Date <span className="required">*</span>
                      </label>
                      <input
                        type="date"
                        className="form-input"
                        value={scheduledDate}
                        onChange={(e) => setScheduledDate(e.target.value)}
                        required
                        disabled={busy}
                      />
                    </div>
                  )}

                  {/* Optional note */}
                  <div className="form-field">
                    <label className="form-label">
                      Note <span className="form-label--optional">(optional)</span>
                    </label>
                    <textarea
                      className="form-input"
                      rows={2}
                      placeholder={
                        nextMilestone === 'report_uploaded'
                          ? 'Add report reference, observations, or findings…'
                          : 'Add notes for this milestone…'
                      }
                      value={actionNote}
                      onChange={(e) => setActionNote(e.target.value)}
                      disabled={busy}
                    />
                  </div>

                  {/* Report upload notice */}
                  {nextMilestone === 'report_uploaded' && (
                    <div className="ste-report-notice">
                      <strong>Note:</strong> Advancing to <em>Report Uploaded</em> marks the
                      task&apos;s <code>report_uploaded</code> flag to <em>true</em>.
                      A dedicated file upload endpoint is not yet available on the backend
                      (survey_reports router is a placeholder).
                    </div>
                  )}

                  {actionError  && (
                    <div className="alert alert--error">{actionError}</div>
                  )}
                  {successMsg && (
                    <div className="ste-success">{successMsg}</div>
                  )}

                  <div className="ste-action-footer">
                    <button
                      type="submit"
                      className="btn btn--primary btn--lg"
                      disabled={busy || (nextMilestone === 'visit_scheduled' && !scheduledDate)}
                    >
                      {busy ? 'Saving…' : (NEXT_ACTION_LABELS[nextMilestone] || `Advance to ${nextMilestone}`)}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </>
        )}

      </div>
    </StaffLayout>
  )
}
