import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import StaffLayout from '../../components/StaffLayout'
import StatusBadge from '../../components/StatusBadge'
import {
  getApplications,
  transitionApplication,
  holdApplication,
  rejectApplication,
  markMissingDocuments,
} from '../../api/staffConsoleApi'
import './ApplicationManagement.css'

const ACTOR_ID = 'staff_console'

const STATUS_OPTIONS = [
  'submitted', 'pre_checked', 'missing_documents', 'on_hold',
  'survey_required', 'surveyed', 'legal_review', 'under_objection',
  'approved', 'certificate_issued', 'rejected', 'closed',
]

// ── Inline action modal ────────────────────────────────────────────────────────
function ActionModal({ open, onClose, title, submitLabel, submitVariant, onSubmit, children, error }) {
  if (!open) return null
  return (
    <div className="mgmt-overlay" onClick={onClose}>
      <div className="mgmt-modal" onClick={(e) => e.stopPropagation()}>
        <div className="mgmt-modal__header">
          <h3 className="mgmt-modal__title">{title}</h3>
          <button className="mgmt-modal__close" type="button" onClick={onClose}>×</button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="mgmt-modal__body">
            {error && <div className="alert alert--error mgmt-modal-err">{error}</div>}
            {children}
          </div>
          <div className="mgmt-modal__footer">
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

// ── Helpers ────────────────────────────────────────────────────────────────────
function parcelNum(ref) {
  if (!ref) return '—'
  if (typeof ref === 'string') return ref
  return ref.parcel_number || '—'
}

function parcelZone(ref) {
  if (!ref || typeof ref === 'string') return '—'
  return ref.zone_id || '—'
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

function allowed(app, state) {
  return (app?.workflow?.allowed_next || []).includes(state)
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function ApplicationManagement() {
  const navigate = useNavigate()

  const [apps, setApps]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  // Filters
  const [fStatus,    setFStatus]    = useState('')
  const [fType,      setFType]      = useState('')
  const [fZone,      setFZone]      = useState('')
  const [fDate,      setFDate]      = useState('')
  const [fApplicant, setFApplicant] = useState('')
  const [fParcel,    setFParcel]    = useState('')

  // Action modal state
  const [modal,        setModal]        = useState({ type: null, app: null })
  const [actionErr,    setActionErr]    = useState(null)
  const [actionBusy,   setActionBusy]   = useState(false)
  const [holdReason,   setHoldReason]   = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [missingInput, setMissingInput] = useState('')

  const loadApps = useCallback(() => {
    setLoading(true)
    setError(null)
    async function fetchAll() {
      const first = await getApplications({ limit: 100, page: 1 })
      const items = [...(first.items || [])]
      const totalPages = first.total > 0 ? Math.ceil(first.total / 100) : 1
      if (totalPages > 1) {
        const extras = await Promise.all(
          Array.from({ length: totalPages - 1 }, (_, i) =>
            getApplications({ limit: 100, page: i + 2 })
          )
        )
        extras.forEach((r) => items.push(...(r.items || [])))
      }
      return items
    }
    fetchAll()
      .then((items) => setApps(items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadApps() }, [loadApps])

  // ── Client-side filtering ──────────────────────────────────────────────────
  const filtered = apps.filter((app) => {
    const pNum  = parcelNum(app.parcel_ref).toLowerCase()
    const zone  = parcelZone(app.parcel_ref).toLowerCase()
    const dStr  = (app.submitted_at || app.created_at || '').slice(0, 10)
    const aType = (app.application_type || '').toLowerCase()

    if (fStatus    && app.status !== fStatus)                                 return false
    if (fType      && !aType.includes(fType.toLowerCase()))                   return false
    if (fZone      && !zone.includes(fZone.toLowerCase()))                    return false
    if (fDate      && dStr !== fDate)                                         return false
    if (fApplicant && !app.applicant_ref.toLowerCase().includes(fApplicant.toLowerCase())) return false
    if (fParcel    && !pNum.includes(fParcel.toLowerCase()))                  return false
    return true
  })

  const clearFilters = () => {
    setFStatus(''); setFType(''); setFZone('')
    setFDate(''); setFApplicant(''); setFParcel('')
  }

  const hasFilters = fStatus || fType || fZone || fDate || fApplicant || fParcel

  // ── Action helpers ─────────────────────────────────────────────────────────
  const closeModal = () => {
    setModal({ type: null, app: null })
    setActionErr(null)
    setHoldReason('')
    setRejectReason('')
    setMissingInput('')
  }

  const handlePrecheck = async (app) => {
    setActionBusy(true)
    setActionErr(null)
    try {
      await transitionApplication(app.application_id, {
        target_state: 'pre_checked',
        actor_type:   'staff',
        actor_id:     ACTOR_ID,
      })
      loadApps()
    } catch (e) {
      setError(`Pre-check failed: ${e.message}`)
    } finally {
      setActionBusy(false)
    }
  }

  const handleHoldSubmit = async (e) => {
    e.preventDefault()
    if (!holdReason.trim()) return
    setActionBusy(true)
    setActionErr(null)
    try {
      await holdApplication(modal.app.application_id, {
        reason:   holdReason.trim(),
        held_by:  ACTOR_ID,
      })
      closeModal()
      loadApps()
    } catch (err) {
      setActionErr(err.message)
    } finally {
      setActionBusy(false)
    }
  }

  const handleRejectSubmit = async (e) => {
    e.preventDefault()
    if (!rejectReason.trim()) return
    setActionBusy(true)
    setActionErr(null)
    try {
      await rejectApplication(modal.app.application_id, {
        reason:      rejectReason.trim(),
        rejected_by: ACTOR_ID,
      })
      closeModal()
      loadApps()
    } catch (err) {
      setActionErr(err.message)
    } finally {
      setActionBusy(false)
    }
  }

  const handleMissingDocsSubmit = async (e) => {
    e.preventDefault()
    const docs = missingInput.split(',').map((d) => d.trim()).filter(Boolean)
    if (!docs.length) return
    setActionBusy(true)
    setActionErr(null)
    try {
      await markMissingDocuments(modal.app.application_id, {
        missing_documents: docs,
      })
      closeModal()
      loadApps()
    } catch (err) {
      setActionErr(err.message)
    } finally {
      setActionBusy(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <StaffLayout>
      <div className="page-container">

        {/* Page header */}
        <div className="mgmt-page-header">
          <div>
            <h1 className="mgmt-page-header__title">Application Management</h1>
            <p className="mgmt-page-header__desc">
              {loading ? 'Loading…' : `${filtered.length} of ${apps.length} application${apps.length !== 1 ? 's' : ''}`}
            </p>
          </div>
          <button className="btn btn--outline" onClick={() => navigate('/staff/dashboard')}>
            ← Dashboard
          </button>
        </div>

        {/* Global action error */}
        {error && (
          <div className="alert alert--error">{error}</div>
        )}

        {/* ── Filter bar ── */}
        <div className="card mgmt-filters-card">
          <div className="mgmt-filters">
            <select
              className="form-input mgmt-filter-input"
              value={fStatus}
              onChange={(e) => setFStatus(e.target.value)}
            >
              <option value="">All Statuses</option>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>

            <input
              type="text"
              className="form-input mgmt-filter-input"
              placeholder="Type (e.g. ownership)"
              value={fType}
              onChange={(e) => setFType(e.target.value)}
            />

            <input
              type="text"
              className="form-input mgmt-filter-input"
              placeholder="Zone (e.g. Z-WEST)"
              value={fZone}
              onChange={(e) => setFZone(e.target.value)}
            />

            <input
              type="date"
              className="form-input mgmt-filter-input"
              value={fDate}
              onChange={(e) => setFDate(e.target.value)}
            />

            <input
              type="text"
              className="form-input mgmt-filter-input"
              placeholder="Applicant ref"
              value={fApplicant}
              onChange={(e) => setFApplicant(e.target.value)}
            />

            <input
              type="text"
              className="form-input mgmt-filter-input"
              placeholder="Parcel number"
              value={fParcel}
              onChange={(e) => setFParcel(e.target.value)}
            />

            {hasFilters && (
              <button type="button" className="btn btn--muted" onClick={clearFilters}>
                Clear
              </button>
            )}
          </div>
        </div>

        {/* ── Table ── */}
        <div className="card mgmt-table-card">
          {loading && (
            <div className="mgmt-loading">Loading applications…</div>
          )}

          {!loading && filtered.length === 0 && (
            <div className="mgmt-empty">
              <div className="mgmt-empty__icon">📋</div>
              <p>{hasFilters ? 'No applications match the current filters.' : 'No applications found.'}</p>
            </div>
          )}

          {!loading && filtered.length > 0 && (
            <div className="mgmt-table-scroll">
              <table className="mgmt-table">
                <thead>
                  <tr>
                    <th>Application ID</th>
                    <th>Applicant</th>
                    <th>Type</th>
                    <th>Parcel</th>
                    <th>Zone</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Submitted</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((app) => (
                    <tr key={app.application_id}>
                      <td>
                        <code className="mgmt-app-id">{app.application_id}</code>
                      </td>
                      <td className="mgmt-td-muted">{app.applicant_ref}</td>
                      <td className="mgmt-td-muted">
                        {app.application_type
                          ? app.application_type.replace(/_/g, ' ')
                          : '—'}
                      </td>
                      <td className="mgmt-td-muted">{parcelNum(app.parcel_ref)}</td>
                      <td className="mgmt-td-muted">{parcelZone(app.parcel_ref)}</td>
                      <td><StatusBadge status={app.status} /></td>
                      <td className="mgmt-td-muted">{app.priority || '—'}</td>
                      <td className="mgmt-td-muted">
                        {formatDate(app.submitted_at || app.created_at)}
                      </td>
                      <td>
                        <div className="mgmt-actions">
                          {/* Open Details — always available */}
                          <button
                            className="mgmt-btn mgmt-btn--view"
                            onClick={() => navigate(`/staff/applications/${app.application_id}`)}
                          >
                            Details
                          </button>

                          {/* Pre-check */}
                          {allowed(app, 'pre_checked') && (
                            <button
                              className="mgmt-btn mgmt-btn--action"
                              disabled={actionBusy}
                              onClick={() => handlePrecheck(app)}
                            >
                              Pre-check
                            </button>
                          )}

                          {/* Request Missing Documents */}
                          {allowed(app, 'missing_documents') && (
                            <button
                              className="mgmt-btn mgmt-btn--warn"
                              onClick={() => setModal({ type: 'missing', app })}
                            >
                              Req. Docs
                            </button>
                          )}

                          {/* Hold */}
                          {allowed(app, 'on_hold') && (
                            <button
                              className="mgmt-btn mgmt-btn--warn"
                              onClick={() => setModal({ type: 'hold', app })}
                            >
                              Hold
                            </button>
                          )}

                          {/* Reject */}
                          {allowed(app, 'rejected') && (
                            <button
                              className="mgmt-btn mgmt-btn--danger"
                              onClick={() => setModal({ type: 'reject', app })}
                            >
                              Reject
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>

      {/* ── Hold modal ── */}
      <ActionModal
        open={modal.type === 'hold'}
        onClose={closeModal}
        title="Place Application on Hold"
        submitLabel="Place on Hold"
        submitVariant="warning"
        onSubmit={handleHoldSubmit}
        error={actionErr}
      >
        <p className="mgmt-modal-app-id">
          Application: <code>{modal.app?.application_id}</code>
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
      </ActionModal>

      {/* ── Reject modal ── */}
      <ActionModal
        open={modal.type === 'reject'}
        onClose={closeModal}
        title="Reject Application"
        submitLabel="Reject"
        submitVariant="danger"
        onSubmit={handleRejectSubmit}
        error={actionErr}
      >
        <p className="mgmt-modal-app-id">
          Application: <code>{modal.app?.application_id}</code>
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
            placeholder="State clearly why the application is being rejected…"
          />
        </div>
      </ActionModal>

      {/* ── Missing documents modal ── */}
      <ActionModal
        open={modal.type === 'missing'}
        onClose={closeModal}
        title="Request Missing Documents"
        submitLabel="Send Request"
        submitVariant="warning"
        onSubmit={handleMissingDocsSubmit}
        error={actionErr}
      >
        <p className="mgmt-modal-app-id">
          Application: <code>{modal.app?.application_id}</code>
        </p>
        <div className="form-field">
          <label className="form-label">
            Missing document names <span className="required">*</span>
          </label>
          <input
            type="text"
            className="form-input"
            required
            value={missingInput}
            onChange={(e) => setMissingInput(e.target.value)}
            placeholder="e.g. national_id, ownership_deed  (comma-separated)"
          />
        </div>
      </ActionModal>

    </StaffLayout>
  )
}
