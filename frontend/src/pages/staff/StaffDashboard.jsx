import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import StaffLayout from '../../components/StaffLayout'
import StatusBadge from '../../components/StatusBadge'
import { getApplications } from '../../api/staffConsoleApi'
import './StaffDashboard.css'

const ALL_STATUSES = [
  'submitted', 'pre_checked', 'missing_documents', 'on_hold',
  'survey_required', 'surveyed', 'legal_review', 'under_objection',
  'approved', 'certificate_issued', 'rejected', 'closed',
]

function StatCard({ icon, label, value, loading, variant }) {
  return (
    <div className={`sd-stat-card sd-stat-card--${variant || 'default'}`}>
      <div className="sd-stat-card__icon">{icon}</div>
      <div className={`sd-stat-card__value${loading ? ' sd-stat-card__value--loading' : ''}`}>
        {loading ? '—' : value}
      </div>
      <div className="sd-stat-card__label">{label}</div>
    </div>
  )
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

export default function StaffDashboard() {
  const navigate = useNavigate()
  const [apps, setApps]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
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

  // ── KPI calculations ───────────────────────────────────────────────────────
  const pending        = apps.filter((a) =>
    ['submitted', 'pre_checked', 'survey_required', 'surveyed', 'on_hold'].includes(a.status)
  ).length
  const legalReview    = apps.filter((a) => a.status === 'legal_review').length
  const missingDocs    = apps.filter((a) => a.status === 'missing_documents').length
  const underObjection = apps.filter((a) => a.status === 'under_objection').length
  const approvedReady  = apps.filter((a) => a.status === 'approved').length

  const recent = [...apps]
    .sort((a, b) =>
      new Date(b.created_at || b.submitted_at) - new Date(a.created_at || a.submitted_at)
    )
    .slice(0, 10)

  return (
    <StaffLayout>
      <div className="page-container">

        {/* ── Page header ── */}
        <div className="sd-page-header">
          <div>
            <h1 className="sd-page-header__title">Staff Console</h1>
            <p className="sd-page-header__desc">
              Land registration workflow — overview and management.
            </p>
          </div>
          <button
            className="btn btn--primary btn--lg"
            onClick={() => navigate('/staff/applications')}
          >
            Manage Applications →
          </button>
        </div>

        {/* ── KPI cards ── */}
        <div className="sd-kpi-grid">
          <StatCard icon="⏱" label="Pending Applications"    value={pending}        loading={loading} variant="pending" />
          <StatCard icon="⚖" label="Legal Review"           value={legalReview}    loading={loading} variant="legal" />
          <StatCard icon="!" label="Missing Documents"       value={missingDocs}    loading={loading} variant="warning" />
          <StatCard icon="📩" label="Under Objection"       value={underObjection} loading={loading} variant="danger" />
          <StatCard icon="✓" label="Approved / Ready"       value={approvedReady}  loading={loading} variant="approved" />
        </div>

        {/* ── Status breakdown ── */}
        <div className="card">
          <h2 className="section-title">Applications by Status</h2>

          {loading && <p className="sd-loading">Loading…</p>}
          {!loading && error && (
            <div className="alert alert--error">Failed to load applications — {error}</div>
          )}
          {!loading && !error && (
            <div className="sd-status-grid">
              {ALL_STATUSES.map((s) => (
                <div key={s} className="sd-status-row">
                  <StatusBadge status={s} />
                  <span className="sd-status-count">
                    {apps.filter((a) => a.status === s).length}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Recent applications ── */}
        <div className="card">
          <div className="sd-section-header">
            <p className="sd-section-label">Recent Applications</p>
            <button
              className="btn btn--outline"
              onClick={() => navigate('/staff/applications')}
            >
              View All
            </button>
          </div>

          {loading && <p className="sd-loading">Loading…</p>}
          {!loading && error && (
            <div className="alert alert--error">Failed to load applications — {error}</div>
          )}
          {!loading && !error && recent.length === 0 && (
            <div className="sd-empty">
              <div className="sd-empty__icon">📋</div>
              <p>No applications found in the system.</p>
            </div>
          )}
          {!loading && !error && recent.length > 0 && (
            <div className="sd-table-scroll">
              <table className="sd-table">
                <thead>
                  <tr>
                    <th>Application ID</th>
                    <th>Applicant</th>
                    <th>Parcel</th>
                    <th>Status</th>
                    <th>Submitted</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((app) => (
                    <tr key={app.application_id}>
                      <td>
                        <code className="sd-app-id">{app.application_id}</code>
                      </td>
                      <td>{app.applicant_ref}</td>
                      <td className="sd-td-muted">{parcelLabel(app.parcel_ref)}</td>
                      <td><StatusBadge status={app.status} /></td>
                      <td className="sd-td-muted">
                        {formatDate(app.submitted_at || app.created_at)}
                      </td>
                      <td>
                        <button
                          className="sd-view-btn"
                          onClick={() => navigate(`/staff/applications/${app.application_id}`)}
                        >
                          View →
                        </button>
                      </td>
                    </tr>
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
