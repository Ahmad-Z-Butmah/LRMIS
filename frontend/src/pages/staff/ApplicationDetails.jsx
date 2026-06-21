import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Polygon } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import StaffLayout from '../../components/StaffLayout'
import StatusBadge from '../../components/StatusBadge'
import Timeline from '../../components/Timeline'
import DocumentReviewPanel from '../../components/DocumentReviewPanel'
import InternalNotes from '../../components/InternalNotes'
import {
  getApplicationById,
  getApplicationTimeline,
  getApplicantById,
  transitionApplication,
  holdApplication,
  rejectApplication,
  markMissingDocuments,
  generateCertificate,
} from '../../api/staffConsoleApi'
import { autoAssignSurveyor } from '../../api/surveyApi'
import './ApplicationDetails.css'

const ACTOR_ID = 'staff_console'

// States handled by transitionApplication (no extra form needed)
const TRANSITION_ACTIONS = {
  pre_checked:     { label: 'Pre-check Application',    variant: 'primary' },
  survey_required: { label: 'Move to Survey Required',  variant: 'primary' },
  surveyed:        { label: 'Mark as Surveyed',         variant: 'primary' },
  legal_review:    { label: 'Move to Legal Review',     variant: 'primary' },
  approved:        { label: 'Approve Application',      variant: 'primary' },
  closed:          { label: 'Close Application',        variant: 'muted'   },
}

// ── Lightweight modal ─────────────────────────────────────────────────────────
function Modal({ open, onClose, title, submitLabel, submitVariant, onSubmit, error, children }) {
  if (!open) return null
  return (
    <div className="ad-overlay" onClick={onClose}>
      <div className="ad-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ad-modal__header">
          <h3 className="ad-modal__title">{title}</h3>
          <button type="button" className="ad-modal__close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="ad-modal__body">
            {error && <div className="alert alert--error">{error}</div>}
            {children}
          </div>
          <div className="ad-modal__footer">
            <button type="button" className="btn btn--muted" onClick={onClose}>Cancel</button>
            <button type="submit" className={`btn btn--${submitVariant || 'primary'}`}>
              {submitLabel || 'Confirm'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Parcel map (read-only) ────────────────────────────────────────────────────
function ParcelMap({ parcelData }) {
  const geometry = parcelData?.geometry
  if (!geometry?.coordinates?.[0]) {
    return (
      <div className="ad-map-placeholder">
        <span className="ad-map-placeholder__icon">🗺</span>
        <p>No parcel geometry available</p>
      </div>
    )
  }
  const ring    = geometry.coordinates[0]
  const latLngs = ring.map(([lng, lat]) => [lat, lng])
  const centerLat = latLngs.reduce((s, c) => s + c[0], 0) / latLngs.length
  const centerLng = latLngs.reduce((s, c) => s + c[1], 0) / latLngs.length

  return (
    <MapContainer
      center={[centerLat, centerLng]}
      zoom={14}
      scrollWheelZoom={false}
      style={{ height: 280, width: '100%', borderRadius: '8px' }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
      />
      <Polygon
        positions={latLngs}
        pathOptions={{ color: '#15532D', fillColor: '#2D6A4F', fillOpacity: 0.2, weight: 2 }}
      />
    </MapContainer>
  )
}

// ── Detail row ────────────────────────────────────────────────────────────────
function MetaRow({ label, value }) {
  return (
    <div className="ad-meta-row">
      <span className="ad-meta-label">{label}</span>
      <span className="ad-meta-value">{value || '—'}</span>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────
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

function parcelLabel(ref) {
  if (!ref) return '—'
  if (typeof ref === 'string') return ref
  return ref.parcel_number || '—'
}

function allowed(app, state) {
  return (app?.workflow?.allowed_next || []).includes(state)
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ApplicationDetails() {
  const { applicationId } = useParams()
  const navigate = useNavigate()

  const [app,       setApp]       = useState(null)
  const [timeline,  setTimeline]  = useState([])
  const [applicant, setApplicant] = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [actionErr, setActionErr] = useState(null)
  const [actionBusy, setActionBusy] = useState(false)

  // Survey assignment state
  const [surveyTask, setSurveyTask] = useState(null)
  const [surveyBusy, setSurveyBusy] = useState(false)
  const [surveyErr,  setSurveyErr]  = useState(null)

  // Modal state
  const [modal,        setModal]        = useState({ type: null })
  const [holdReason,   setHoldReason]   = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [missingInput, setMissingInput] = useState('')
  const [confirmState, setConfirmState] = useState('')  // for simple transitions

  // Certificate form state
  const [certType,     setCertType]     = useState('ownership')
  const [certFullName, setCertFullName] = useState('')
  const [certNatId,    setCertNatId]    = useState('')
  const [certAddress,  setCertAddress]  = useState('')
  const [certIssuedBy, setCertIssuedBy] = useState('staff_console')

  // ── Load application ───────────────────────────────────────────────────────
  const loadApp = () => {
    if (!applicationId) return
    setLoading(true)
    setError(null)
    getApplicationById(applicationId)
      .then((data) => {
        setApp(data)
        // Load timeline via Student 2 endpoint
        return getApplicationTimeline(applicationId).catch(() => null)
      })
      .then((tData) => {
        if (tData) {
          const events = Array.isArray(tData)
            ? tData
            : (tData.events || tData.timeline || tData.audit_timeline || [])
          if (events.length > 0) setTimeline(events)
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadApp() }, [applicationId])   // eslint-disable-line react-hooks/exhaustive-deps

  // Load applicant once app is available
  useEffect(() => {
    if (!app?.applicant_ref) return
    getApplicantById(app.applicant_ref)
      .then((data) => setApplicant(data))
      .catch(() => null)  // supplementary — silent fail is acceptable
  }, [app?.applicant_ref])

  // Pre-populate certificate form from applicant data
  useEffect(() => {
    if (!applicant) return
    setCertFullName(applicant.full_name || '')
    setCertNatId(applicant.national_id || '')
    if (applicant.address) {
      const a = applicant.address
      setCertAddress([a.street, a.neighborhood, a.city].filter(Boolean).join(', '))
    }
  }, [applicant])

  // ── Modal helpers ──────────────────────────────────────────────────────────
  const closeModal = () => {
    setModal({ type: null })
    setActionErr(null)
    setHoldReason('')
    setRejectReason('')
    setMissingInput('')
    setConfirmState('')
    setCertType('ownership')
    setCertFullName('')
    setCertNatId('')
    setCertAddress('')
    setCertIssuedBy('staff_console')
  }

  // ── Action handlers ────────────────────────────────────────────────────────
  const doTransition = async (e) => {
    e.preventDefault()
    setActionBusy(true)
    setActionErr(null)
    try {
      await transitionApplication(app.application_id, {
        target_state: confirmState,
        actor_type:   'staff',
        actor_id:     ACTOR_ID,
      })
      closeModal()
      loadApp()
    } catch (err) {
      setActionErr(err.message)
    } finally {
      setActionBusy(false)
    }
  }

  const doGenerateCertificate = async (e) => {
    e.preventDefault()
    setActionBusy(true)
    setActionErr(null)
    try {
      await generateCertificate(app.application_id, {
        certificate_type: certType,
        issued_to: {
          full_name:   certFullName.trim(),
          national_id: certNatId.trim(),
          address:     certAddress.trim(),
        },
        issued_by: certIssuedBy.trim() || ACTOR_ID,
      })
      closeModal()
      loadApp()
    } catch (err) {
      setActionErr(err.message)
    } finally {
      setActionBusy(false)
    }
  }

  const doHold = async (e) => {
    e.preventDefault()
    if (!holdReason.trim()) return
    setActionBusy(true)
    setActionErr(null)
    try {
      await holdApplication(app.application_id, {
        reason:  holdReason.trim(),
        held_by: ACTOR_ID,
      })
      closeModal()
      loadApp()
    } catch (err) {
      setActionErr(err.message)
    } finally {
      setActionBusy(false)
    }
  }

  const doReject = async (e) => {
    e.preventDefault()
    if (!rejectReason.trim()) return
    setActionBusy(true)
    setActionErr(null)
    try {
      await rejectApplication(app.application_id, {
        reason:      rejectReason.trim(),
        rejected_by: ACTOR_ID,
      })
      closeModal()
      loadApp()
    } catch (err) {
      setActionErr(err.message)
    } finally {
      setActionBusy(false)
    }
  }

  const doAutoAssign = async () => {
    setSurveyBusy(true)
    setSurveyErr(null)
    try {
      const result = await autoAssignSurveyor(app.application_id)
      setSurveyTask(result)
      loadApp()
    } catch (err) {
      setSurveyErr(err.message)
    } finally {
      setSurveyBusy(false)
    }
  }

  const doMissingDocs = async (e) => {
    e.preventDefault()
    const docs = missingInput.split(',').map((d) => d.trim()).filter(Boolean)
    if (!docs.length) return
    setActionBusy(true)
    setActionErr(null)
    try {
      await markMissingDocuments(app.application_id, { missing_documents: docs })
      closeModal()
      loadApp()
    } catch (err) {
      setActionErr(err.message)
    } finally {
      setActionBusy(false)
    }
  }

  // ── Derived data ───────────────────────────────────────────────────────────
  const auditEvents = timeline.length > 0 ? timeline : (app?.audit_timeline || [])
  const publicNotes   = (app?.internal_notes || [])
  const parcelData    = app?.parcel_data
  const allowedNext   = app?.workflow?.allowed_next || []

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <StaffLayout>
      <div className="page-container">

        {/* Back nav */}
        <div className="ad-back-row">
          <button className="btn btn--muted" onClick={() => navigate('/staff/applications')}>
            ← Applications
          </button>
        </div>

        {loading && (
          <div className="card ad-loading-card">
            <div className="ad-spinner" />
            <p>Loading application…</p>
          </div>
        )}

        {!loading && error && (
          <div className="alert alert--error">
            Could not load application — {error}
          </div>
        )}

        {!loading && actionErr && (
          <div className="alert alert--error">
            Action failed — {actionErr}
            <button
              className="ad-dismiss"
              onClick={() => setActionErr(null)}
            >×</button>
          </div>
        )}

        {!loading && app && (
          <>
            {/* ── Status hero ── */}
            <div className="ad-hero card">
              <div className="ad-hero__left">
                <p className="ad-hero__label">Application ID</p>
                <code className="ad-hero__app-id">{app.application_id}</code>
              </div>
              <div className="ad-hero__center">
                <p className="ad-hero__label">Current Status</p>
                <StatusBadge status={app.status} />
              </div>
              <div className="ad-hero__right">
                <MetaRow label="Submitted"    value={formatDate(app.submitted_at)} />
                <MetaRow label="Last Updated" value={formatDate(app.updated_at)} />
              </div>
            </div>

            {/* ── Workflow action bar ── */}
            {allowedNext.length > 0 && (
              <div className="card ad-action-bar">
                <p className="ad-action-bar__label">Allowed Actions</p>
                <div className="ad-action-bar__btns">

                  {/* Simple transitions */}
                  {allowedNext
                    .filter((s) => TRANSITION_ACTIONS[s])
                    .map((s) => (
                      <button
                        key={s}
                        disabled={actionBusy}
                        className={`btn btn--${TRANSITION_ACTIONS[s].variant}`}
                        onClick={() => {
                          setConfirmState(s)
                          setModal({ type: 'confirm' })
                        }}
                      >
                        {TRANSITION_ACTIONS[s].label}
                      </button>
                    ))}

                  {/* Issue Certificate */}
                  {allowed(app, 'certificate_issued') && (
                    <button
                      disabled={actionBusy}
                      className="btn btn--primary"
                      onClick={() => setModal({ type: 'certificate' })}
                    >
                      Issue Certificate
                    </button>
                  )}

                  {/* Request Missing Documents */}
                  {allowed(app, 'missing_documents') && (
                    <button
                      disabled={actionBusy}
                      className="btn btn--warning"
                      onClick={() => setModal({ type: 'missing' })}
                    >
                      Request Missing Documents
                    </button>
                  )}

                  {/* Place on Hold */}
                  {allowed(app, 'on_hold') && (
                    <button
                      disabled={actionBusy}
                      className="btn btn--warning"
                      onClick={() => setModal({ type: 'hold' })}
                    >
                      Place on Hold
                    </button>
                  )}

                  {/* Reject */}
                  {allowed(app, 'rejected') && (
                    <button
                      disabled={actionBusy}
                      className="btn btn--danger"
                      onClick={() => setModal({ type: 'reject' })}
                    >
                      Reject
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* ── Applicant + Parcel grid ── */}
            <div className="ad-two-col">

              {/* Applicant details */}
              <div className="card">
                <h2 className="section-title">Applicant Details</h2>
                <MetaRow label="Applicant Ref" value={app.applicant_ref} />
                {applicant ? (
                  <>
                    <MetaRow label="Full Name"    value={applicant.full_name} />
                    <MetaRow label="Type"         value={applicant.applicant_type} />
                    <MetaRow label="Verified"     value={applicant.verification_state} />
                    {applicant.contacts && (
                      <>
                        <MetaRow label="Email" value={applicant.contacts.email} />
                        <MetaRow label="Phone" value={applicant.contacts.phone} />
                      </>
                    )}
                    {applicant.address && (
                      <MetaRow
                        label="Address"
                        value={`${applicant.address.neighborhood}, ${applicant.address.city}`}
                      />
                    )}
                  </>
                ) : (
                  <p className="ad-supplementary">Full profile not available for this applicant.</p>
                )}
              </div>

              {/* Parcel details */}
              <div className="card">
                <h2 className="section-title">Parcel Details</h2>
                <MetaRow label="Parcel Number" value={parcelLabel(app.parcel_ref)} />
                {typeof app.parcel_ref === 'object' && app.parcel_ref && (
                  <>
                    <MetaRow label="Zone"         value={app.parcel_ref.zone_id} />
                    <MetaRow label="Block"        value={app.parcel_ref.block_number} />
                    <MetaRow label="Basin"        value={app.parcel_ref.basin_number} />
                  </>
                )}
                {parcelData && (
                  <>
                    <MetaRow label="Zone"     value={parcelData.zone_id} />
                    <MetaRow label="Block"    value={parcelData.block_number} />
                    <MetaRow label="Basin"    value={parcelData.basin_number} />
                    <MetaRow label="Area"     value={parcelData.area_sqm ? `${parcelData.area_sqm} m²` : null} />
                  </>
                )}
                <MetaRow label="App. Type" value={app.application_type?.replace(/_/g, ' ')} />
              </div>
            </div>

            {/* ── Processing status ── */}
            {(app.survey_status || app.objection_status || app.certificate_status) && (
              <div className="card">
                <h2 className="section-title">Processing Status</h2>
                <div className="ad-status-pills">
                  {app.survey_status && (
                    <div className="ad-status-pill">
                      <span className="ad-status-pill__key">Survey</span>
                      <span className="ad-status-pill__val">
                        {app.survey_status.replace(/_/g, ' ')}
                      </span>
                    </div>
                  )}
                  {app.objection_status && (
                    <div className="ad-status-pill ad-status-pill--warn">
                      <span className="ad-status-pill__key">Objection</span>
                      <span className="ad-status-pill__val">
                        {app.objection_status.replace(/_/g, ' ')}
                      </span>
                    </div>
                  )}
                  {app.certificate_status && (
                    <div className="ad-status-pill ad-status-pill--ok">
                      <span className="ad-status-pill__key">Certificate</span>
                      <span className="ad-status-pill__val">
                        {app.certificate_status.replace(/_/g, ' ')}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── Survey Assignment ── */}
            {(app.status === 'survey_required' || surveyTask || app.survey_task_id || app.assigned_surveyor_id) && (
              <div className="card">
                <h2 className="section-title">Survey Assignment</h2>

                {/* Result from this session */}
                {surveyTask && (
                  <div className="ad-survey-result">
                    <span className="ad-survey-result__badge">Surveyor assigned successfully</span>
                    <MetaRow label="Task ID"     value={surveyTask.task_id} />
                    <MetaRow label="Surveyor ID" value={surveyTask.assigned_surveyor_id} />
                    <MetaRow label="Task Status" value={surveyTask.status?.replace(/_/g, ' ')} />
                    {surveyTask.score != null && (
                      <MetaRow label="Match Score" value={String(surveyTask.score)} />
                    )}
                  </div>
                )}

                {/* Pre-existing assignment already on the application */}
                {!surveyTask && (app.survey_task_id || app.assigned_surveyor_id) && (
                  <div className="ad-survey-result">
                    <span className="ad-survey-result__badge ad-survey-result__badge--info">Surveyor already assigned</span>
                    {app.survey_task_id && <MetaRow label="Task ID"      value={app.survey_task_id} />}
                    {app.assigned_surveyor_id && <MetaRow label="Surveyor ID" value={app.assigned_surveyor_id} />}
                    {app.survey_status && <MetaRow label="Survey Status" value={app.survey_status.replace(/_/g, ' ')} />}
                  </div>
                )}

                {/* Auto-assign button — only when status is survey_required and not yet assigned */}
                {app.status === 'survey_required' && !surveyTask && !app.assigned_surveyor_id && (
                  <>
                    <p className="ad-supplementary">
                      Automatically assign the most suitable available surveyor based on workload and proximity.
                    </p>
                    {surveyErr && (
                      <div className="alert alert--error">
                        {surveyErr}
                        <button className="ad-dismiss" onClick={() => setSurveyErr(null)}>×</button>
                      </div>
                    )}
                    <div className="ad-survey-actions">
                      <button
                        className="btn btn--primary"
                        disabled={surveyBusy}
                        onClick={doAutoAssign}
                      >
                        {surveyBusy ? 'Assigning…' : 'Auto Assign Surveyor'}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* ── Documents ── */}
            <div className="card">
              <h2 className="section-title">Uploaded Documents</h2>
              <DocumentReviewPanel
                documents={app.documents || []}
                applicationId={applicationId}
                onRefresh={loadApp}
              />
            </div>

            {/* ── Map preview ── */}
            <div className="card">
              <h2 className="section-title">Parcel Map</h2>
              <ParcelMap parcelData={parcelData} />
            </div>

            {/* ── Internal notes ── */}
            <div className="card">
              <h2 className="section-title">Internal Notes</h2>
              <InternalNotes
                notes={publicNotes}
                applicationId={applicationId}
                onNoteAdded={loadApp}
              />
            </div>

            {/* ── Timeline ── */}
            <div className="card">
              <h2 className="section-title">Status Timeline</h2>
              <Timeline
                currentStatus={app.status}
                auditTimeline={auditEvents}
              />
            </div>
          </>
        )}
      </div>

      {/* ─── Modals ──────────────────────────────────────────────────────────── */}

      {/* Simple transition confirm */}
      <Modal
        open={modal.type === 'confirm'}
        onClose={closeModal}
        title={TRANSITION_ACTIONS[confirmState]?.label || 'Confirm Action'}
        submitLabel="Confirm"
        submitVariant={TRANSITION_ACTIONS[confirmState]?.variant || 'primary'}
        onSubmit={doTransition}
        error={actionErr}
      >
        <p className="ad-modal-msg">
          Move <code className="ad-modal-id">{app?.application_id}</code> to{' '}
          <strong>{confirmState.replace(/_/g, ' ')}</strong>?
        </p>
      </Modal>

      {/* Issue certificate */}
      <Modal
        open={modal.type === 'certificate'}
        onClose={closeModal}
        title="Issue Certificate"
        submitLabel="Issue Certificate"
        submitVariant="primary"
        onSubmit={doGenerateCertificate}
        error={actionErr}
      >
        <p className="ad-modal-msg">
          Certificate for <code className="ad-modal-id">{app?.application_id}</code>
        </p>
        <div className="form-field">
          <label className="form-label">Certificate Type <span className="required">*</span></label>
          <select
            className="form-input"
            required
            value={certType}
            onChange={(e) => setCertType(e.target.value)}
          >
            <option value="ownership">Ownership</option>
            <option value="lease">Lease</option>
            <option value="provisional">Provisional</option>
          </select>
        </div>
        <div className="form-field">
          <label className="form-label">Holder Full Name <span className="required">*</span></label>
          <input
            type="text"
            className="form-input"
            required
            value={certFullName}
            onChange={(e) => setCertFullName(e.target.value)}
            placeholder="Full legal name of the certificate holder"
          />
        </div>
        <div className="form-field">
          <label className="form-label">National ID <span className="required">*</span></label>
          <input
            type="text"
            className="form-input"
            required
            value={certNatId}
            onChange={(e) => setCertNatId(e.target.value)}
            placeholder="National ID number"
          />
        </div>
        <div className="form-field">
          <label className="form-label">Registered Address <span className="required">*</span></label>
          <input
            type="text"
            className="form-input"
            required
            value={certAddress}
            onChange={(e) => setCertAddress(e.target.value)}
            placeholder="Registered address of the holder"
          />
        </div>
        <div className="form-field">
          <label className="form-label">Issued By <span className="required">*</span></label>
          <input
            type="text"
            className="form-input"
            required
            value={certIssuedBy}
            onChange={(e) => setCertIssuedBy(e.target.value)}
          />
        </div>
      </Modal>

      {/* Hold */}
      <Modal
        open={modal.type === 'hold'}
        onClose={closeModal}
        title="Place Application on Hold"
        submitLabel="Place on Hold"
        submitVariant="warning"
        onSubmit={doHold}
        error={actionErr}
      >
        <p className="ad-modal-msg">
          Application: <code className="ad-modal-id">{app?.application_id}</code>
        </p>
        <div className="form-field">
          <label className="form-label">
            Reason <span className="required">*</span>
          </label>
          <textarea
            className="form-input"
            rows={3}
            required
            value={holdReason}
            onChange={(e) => setHoldReason(e.target.value)}
            placeholder="Enter reason for placing on hold…"
          />
        </div>
      </Modal>

      {/* Reject */}
      <Modal
        open={modal.type === 'reject'}
        onClose={closeModal}
        title="Reject Application"
        submitLabel="Reject"
        submitVariant="danger"
        onSubmit={doReject}
        error={actionErr}
      >
        <p className="ad-modal-msg">
          Application: <code className="ad-modal-id">{app?.application_id}</code>
        </p>
        <div className="form-field">
          <label className="form-label">
            Rejection reason <span className="required">*</span>
          </label>
          <textarea
            className="form-input"
            rows={3}
            required
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="State clearly why the application is rejected…"
          />
        </div>
      </Modal>

      {/* Missing documents */}
      <Modal
        open={modal.type === 'missing'}
        onClose={closeModal}
        title="Request Missing Documents"
        submitLabel="Send Request"
        submitVariant="warning"
        onSubmit={doMissingDocs}
        error={actionErr}
      >
        <p className="ad-modal-msg">
          Application: <code className="ad-modal-id">{app?.application_id}</code>
        </p>
        <div className="form-field">
          <label className="form-label">
            Missing documents <span className="required">*</span>
          </label>
          <input
            type="text"
            className="form-input"
            required
            value={missingInput}
            onChange={(e) => setMissingInput(e.target.value)}
            placeholder="national_id, ownership_deed  (comma-separated)"
          />
        </div>
      </Modal>


    </StaffLayout>
  )
}
