import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'
import { fetchApplications } from '../../api/applicationsApi'
import './ApplicantDashboard.css'

function StatCard({ label, value, loading, variant, icon }) {
  return (
    <div className={`stat-card stat-card--${variant || 'default'}`}>
      <div className="stat-card__icon">{icon}</div>
      <div className={`stat-card__value${loading ? ' stat-card__value--loading' : ''}`}>
        {loading ? '—' : value}
      </div>
      <div className="stat-card__label">{label}</div>
    </div>
  )
}

function ActionCard({ icon, iconVariant, title, desc, onClick }) {
  return (
    <button className="action-card" onClick={onClick} type="button">
      <div className={`action-card__icon action-card__icon--${iconVariant || 'secondary'}`}>
        {icon}
      </div>
      <div className="action-card__body">
        <p className="action-card__title">{title}</p>
        <p className="action-card__desc">{desc}</p>
      </div>
    </button>
  )
}

export default function ApplicantDashboard() {
  const navigate = useNavigate()
  const [apps, setApps]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    fetchApplications({ limit: 100 })
      .then((data) => setApps(data.items || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const pending = apps.filter((a) =>
    ['submitted', 'pre_checked', 'survey_required', 'surveyed', 'legal_review', 'on_hold'].includes(a.status),
  ).length

  const approved    = apps.filter((a) => ['approved', 'certificate_issued'].includes(a.status)).length
  const missingDocs = apps.filter((a) => a.status === 'missing_documents').length

  const recent = [...apps]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5)

  const formatDate = (iso) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  }

  const parcelLabel = (parcelRef) => {
    if (!parcelRef) return '—'
    if (typeof parcelRef === 'string') return parcelRef
    return parcelRef.parcel_number || '—'
  }

  return (
    <Layout>
      <div className="page-container">

        {/* ── Page header ── */}
        <div className="dash-page-header">
          <div>
            <h1 className="dash-page-header__title">Applicant Dashboard</h1>
            <p className="dash-page-header__desc">
              Submit, track, and manage your land registration applications.
            </p>
          </div>
          <button className="btn btn--primary btn--lg" onClick={() => navigate('/applicant/submit')}>
            + New Application
          </button>
        </div>

        {/* ── Stat cards ── */}
        <div className="stat-cards">
          <StatCard icon="≡" label="Total Applications" value={apps.length} loading={loading} variant="total" />
          <StatCard icon="⏱" label="In Progress"        value={pending}     loading={loading} variant="pending" />
          <StatCard icon="✓" label="Approved"           value={approved}    loading={loading} variant="approved" />
          <StatCard icon="!" label="Missing Documents"  value={missingDocs} loading={loading} variant="warning" />
        </div>

        {/* ── Quick actions ── */}
        <div className="card">
          <h2 className="section-title">Quick Actions</h2>
          <div className="quick-actions">
            <ActionCard
              icon="+"
              iconVariant="primary"
              title="Submit New Application"
              desc="Start a new land registration request"
              onClick={() => navigate('/applicant/submit')}
            />
            <ActionCard
              icon="→"
              iconVariant="secondary"
              title="Track Application"
              desc="Look up status by Application ID"
              onClick={() => navigate('/applicant/track')}
            />
            <ActionCard
              icon="↑"
              iconVariant="secondary"
              title="Upload Documents"
              desc="Attach required documents to a pending application"
              onClick={() => navigate('/applicant/upload-documents')}
            />
          </div>
        </div>

        {/* ── Recent applications ── */}
        <div className="card">
          <h2 className="section-title">Recent Applications</h2>

          {loading && <p className="loading-text">Loading applications…</p>}

          {!loading && error && (
            <div className="alert alert--error">Unable to load applications — {error}</div>
          )}

          {!loading && !error && recent.length === 0 && (
            <div className="empty-state">
              <div className="empty-state__icon">📋</div>
              <p>No applications yet.</p>
              <button className="btn btn--primary" onClick={() => navigate('/applicant/submit')}>
                Submit your first application
              </button>
            </div>
          )}

          {!loading && !error && recent.length > 0 && (
            <div className="table-scroll">
              <table className="recent-table">
                <thead>
                  <tr>
                    <th>Application ID</th>
                    <th>Parcel No.</th>
                    <th>Status</th>
                    <th>Applicant Ref</th>
                    <th>Submitted</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((app) => (
                    <tr key={app.application_id}>
                      <td><code className="app-id-code">{app.application_id}</code></td>
                      <td>{parcelLabel(app.parcel_ref)}</td>
                      <td><StatusBadge status={app.status} /></td>
                      <td className="td-muted">{app.applicant_ref}</td>
                      <td className="td-muted">{formatDate(app.submitted_at || app.created_at)}</td>
                      <td>
                        <button
                          className="view-btn"
                          onClick={() => navigate(`/applicant/track/${app.application_id}`)}
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
    </Layout>
  )
}
