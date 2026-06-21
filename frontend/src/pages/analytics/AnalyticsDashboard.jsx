import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import StaffLayout from '../../components/StaffLayout'
import StatusBadge from '../../components/StatusBadge'
import {
  getKpis,
  getApplicationsByStatus,
  getApplicationsByZone,
  getApplicationsDerived,
  getProcessingTime,
  getSurveyorAnalytics,
  getRegistrarAnalytics,
  getCertificatesPerMonth,
  getDelayedApplications,
} from '../../api/analyticsApi'
import './AnalyticsDashboard.css'

// ─── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, variant, loading }) {
  return (
    <div className={`ad-kpi ad-kpi--${variant || 'default'}`}>
      <div className={`ad-kpi__value${loading ? ' ad-kpi__value--loading' : ''}`}>
        {loading ? '—' : (value ?? '—')}
      </div>
      <div className="ad-kpi__label">{label}</div>
      {sub && <div className="ad-kpi__sub">{sub}</div>}
    </div>
  )
}

// ─── CSS horizontal bar chart ─────────────────────────────────────────────────

function HBarChart({ data, labelKey, valueKey, colorFn, limit = 15 }) {
  if (!data?.length) return <p className="ad-empty">No data available.</p>
  const rows = data.slice(0, limit)
  const max = Math.max(...rows.map((d) => d[valueKey] || 0), 1)
  return (
    <div className="ad-hbar">
      {rows.map((row, i) => {
        const pct = Math.max(2, Math.round(((row[valueKey] || 0) / max) * 100))
        const fillColor = colorFn ? colorFn(row) : 'var(--color-primary)'
        return (
          <div key={i} className="ad-hbar__row">
            <span className="ad-hbar__label" title={String(row[labelKey])}>
              {String(row[labelKey]).replace(/_/g, ' ')}
            </span>
            <div className="ad-hbar__track">
              <div className="ad-hbar__fill" style={{ width: `${pct}%`, background: fillColor }} />
            </div>
            <span className="ad-hbar__count">{row[valueKey]}</span>
          </div>
        )
      })}
    </div>
  )
}

// ─── CSS vertical bar chart (monthly data) ────────────────────────────────────

function VBarChart({ data }) {
  if (!data?.length) return <p className="ad-empty">No data available.</p>
  const max = Math.max(...data.map((d) => d.count || 0), 1)
  return (
    <div className="ad-vchart">
      {data.map((row, i) => {
        const pctH = Math.max(4, Math.round(((row.count || 0) / max) * 100))
        return (
          <div key={i} className="ad-vchart__col">
            <span className="ad-vchart__count">{row.count}</span>
            <div className="ad-vchart__bar" style={{ height: `${pctH}%` }} />
            <span className="ad-vchart__label">{(row.month || '').substring(2)}</span>
          </div>
        )
      })}
    </div>
  )
}

// ─── Workload progress bar ────────────────────────────────────────────────────

function WorkloadBar({ pct }) {
  const clamped = Math.min(Math.max(pct || 0, 0), 100)
  const fill = clamped >= 90 ? '#DC2626' : clamped >= 70 ? '#D97706' : '#15532D'
  return (
    <div className="ad-wbar">
      <div className="ad-wbar__fill" style={{ width: `${clamped}%`, background: fill }} />
    </div>
  )
}

// ─── Section card wrapper ─────────────────────────────────────────────────────

function Section({ title, children, error }) {
  return (
    <div className="card">
      <h2 className="section-title">{title}</h2>
      {error && <div className="alert alert--error" style={{ margin: 0 }}>{error}</div>}
      {!error && children}
    </div>
  )
}

// ─── Surveyor workload section ────────────────────────────────────────────────

function SurveyorWorkload({ data }) {
  const list = data?.surveyors || []
  if (!list.length) return <p className="ad-empty">No surveyor data.</p>
  return (
    <div className="ad-table-wrap">
      <table className="ad-table">
        <thead>
          <tr>
            <th>Surveyor</th>
            <th>Active</th>
            <th>Completed</th>
            <th>Max</th>
            <th>Workload</th>
            <th>Avg Days</th>
            <th>Reports</th>
          </tr>
        </thead>
        <tbody>
          {list.map((s) => {
            const pct = s.workload_percentage || 0
            const rowClass = pct >= 90 ? 'ad-tr--danger' : pct >= 70 ? 'ad-tr--warn' : ''
            return (
              <tr key={s.surveyor_id} className={rowClass}>
                <td>
                  <div className="ad-surveyor-name">{s.surveyor_name || s.surveyor_id}</div>
                  <div className="ad-surveyor-id">{s.surveyor_id}</div>
                </td>
                <td className="ad-td-num">{s.active_tasks}</td>
                <td className="ad-td-num">{s.completed_tasks}</td>
                <td className="ad-td-num ad-td-muted">{s.max_tasks}</td>
                <td>
                  <div className="ad-wbar-cell">
                    <WorkloadBar pct={pct} />
                    <span className={`ad-wbar-label${pct >= 90 ? ' ad-wbar-label--danger' : pct >= 70 ? ' ad-wbar-label--warn' : ''}`}>
                      {pct}%
                    </span>
                  </div>
                </td>
                <td className="ad-td-num">
                  {s.average_task_completion_days > 0 ? `${s.average_task_completion_days}d` : '—'}
                </td>
                <td className="ad-td-num">{s.reports_uploaded}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── Registrar analytics section ──────────────────────────────────────────────

function RegistrarAnalytics({ data }) {
  const list = data?.registrars || []
  if (!list.length) return <p className="ad-empty">No registrar data.</p>
  return (
    <>
      {data.registrars[0]?.assigned_reviews_is_proxy && (
        <div className="ad-proxy-note">
          Assigned reviews count is a global proxy — no per-registrar assignment field in schema.
        </div>
      )}
      <div className="ad-table-wrap">
        <table className="ad-table">
          <thead>
            <tr>
              <th>Registrar</th>
              <th>Assigned (proxy)</th>
              <th>Completed</th>
              <th>Approved</th>
              <th>Rejected</th>
              <th>Avg Review (days)</th>
            </tr>
          </thead>
          <tbody>
            {list.map((r) => (
              <tr key={r.registrar_id}>
                <td>
                  <div className="ad-surveyor-name">{r.registrar_name || r.registrar_id}</div>
                  <div className="ad-surveyor-id">{r.registrar_id}</div>
                </td>
                <td className="ad-td-num ad-td-muted">{r.assigned_reviews}</td>
                <td className="ad-td-num">{r.completed_reviews}</td>
                <td className="ad-td-num ad-td-green">{r.approved_count}</td>
                <td className="ad-td-num ad-td-red">{r.rejected_count}</td>
                <td className="ad-td-num">
                  {r.average_review_time > 0 ? `${r.average_review_time}d` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

// ─── Delayed applications table ───────────────────────────────────────────────

function DelayedApplicationsTable({ data }) {
  if (!Array.isArray(data)) return <p className="ad-empty">Loading delayed applications…</p>
  if (!data.length) return <p className="ad-empty">No applications delayed beyond 7 days.</p>
  return (
    <div className="ad-table-wrap">
      <table className="ad-table">
        <thead>
          <tr>
            <th>Application ID</th>
            <th>Status</th>
            <th>Type</th>
            <th>Zone</th>
            <th>Parcel</th>
            <th>Submitted</th>
            <th>Delayed (days)</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.application_id} className={row.delayed_days >= 30 ? 'ad-tr--danger' : 'ad-tr--warn'}>
              <td className="ad-td-mono">{row.application_id}</td>
              <td><StatusBadge status={row.status} /></td>
              <td>{(row.application_type || '—').replace(/_/g, ' ')}</td>
              <td className="ad-td-muted">{row.zone_id || '—'}</td>
              <td className="ad-td-muted">{row.parcel_number || '—'}</td>
              <td className="ad-td-muted">
                {row.submitted_at ? row.submitted_at.substring(0, 10) : '—'}
              </td>
              <td className="ad-td-num ad-td-red">{row.delayed_days}d</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Status color helper for bar chart ───────────────────────────────────────

function statusColor(row) {
  const s = row.status
  if (s === 'under_objection' || s === 'rejected') return '#DC2626'
  if (s === 'approved' || s === 'certificate_issued' || s === 'surveyed') return '#15532D'
  if (s === 'survey_required' || s === 'missing_documents') return '#D97706'
  if (s === 'legal_review') return '#5B21B6'
  return 'var(--color-accent)'
}

// ─── Main dashboard ───────────────────────────────────────────────────────────

export default function AnalyticsDashboard() {
  const navigate = useNavigate()
  const [kpis,          setKpis]          = useState(null)
  const [byStatus,      setByStatus]      = useState(null)
  const [byZone,        setByZone]        = useState(null)
  const [overTime,      setOverTime]      = useState(null)
  const [byZoneSource,  setByZoneSource]  = useState(null)
  const [processingTime,setProcessingTime]= useState(null)
  const [surveyors,     setSurveyors]     = useState(null)
  const [registrars,    setRegistrars]    = useState(null)
  const [certsPerMonth, setCertsPerMonth] = useState(null)
  const [delayedApps,   setDelayedApps]  = useState(null)
  const [errors,        setErrors]        = useState({})
  const [loading,       setLoading]       = useState(true)

  useEffect(() => {
    Promise.allSettled([
      getKpis(),
      getApplicationsByStatus(),
      getApplicationsByZone(),
      getProcessingTime(),
      getSurveyorAnalytics(),
      getRegistrarAnalytics(),
      getCertificatesPerMonth(),
      getDelayedApplications(7),
      getApplicationsDerived(),
    ]).then(([kR, bsR, bzR, ptR, svR, rgR, cmR, dlR, dR]) => {
      const errs = {}
      if (kR.status  === 'fulfilled') setKpis(kR.value)
      else errs.kpis = kR.reason.message

      if (bsR.status === 'fulfilled') setByStatus(bsR.value)
      else errs.derived = bsR.reason.message

      if (bzR.status === 'fulfilled') setByZone(bzR.value)
      else if (!errs.derived) errs.derived = bzR.reason.message

      if (ptR.status === 'fulfilled') setProcessingTime(ptR.value)
      else errs.pt = ptR.reason.message

      if (svR.status === 'fulfilled') setSurveyors(svR.value)
      else errs.surveyors = svR.reason.message

      if (rgR.status === 'fulfilled') setRegistrars(rgR.value)
      else errs.registrars = rgR.reason.message

      if (cmR.status === 'fulfilled') setCertsPerMonth(cmR.value)
      else errs.certs = cmR.reason.message

      if (dlR.status === 'fulfilled') setDelayedApps(dlR.value)
      else errs.delayed = dlR.reason.message

      if (dR.status === 'fulfilled') {
        setOverTime(dR.value?.overTime || [])
        setByZoneSource(dR.value?.byZoneSource || null)
      }

      setErrors(errs)
      setLoading(false)
    })
  }, [])

  const underObjectionCount =
    byStatus?.find((d) => d.status === 'under_objection')?.count ?? 0

  return (
    <StaffLayout>
      <div className="page-container">

        {/* ── Page header ── */}
        <div className="ad-header">
          <div>
            <h1 className="ad-header__title">Analytics Dashboard</h1>
            <p className="ad-header__desc">
              Land registration performance — KPIs, workload, and processing metrics
            </p>
          </div>
          <div className="ad-header__actions">
            <button className="btn btn--outline" onClick={() => navigate('/surveyor/tasks')}>
              Surveyor Tasks
            </button>
            <button className="btn btn--outline" onClick={() => navigate('/map/live')}>
              Live Map
            </button>
          </div>
        </div>

        {/* ── Global loading ── */}
        {loading && (
          <div className="ad-loading">
            <div className="ad-spinner" />
            <p>Loading analytics…</p>
          </div>
        )}

        {/* ── KPI cards ── */}
        {!loading && (
          <div className="ad-kpi-grid">
            <KpiCard label="Total Applications"  value={kpis?.total_applications}  variant="default"  />
            <KpiCard label="Pending"             value={kpis?.pending_applications} variant="pending"  />
            <KpiCard label="Survey Required"     value={kpis?.survey_required}      variant="survey"   />
            <KpiCard label="Active Survey Tasks" value={kpis?.active_survey_tasks}  variant="tasks"    />
            <KpiCard label="Approved"            value={kpis?.approved_count}       variant="approved" />
            <KpiCard label="Rejected"            value={kpis?.rejected_count}       variant="danger"   />
            <KpiCard label="Certs Issued"        value={kpis?.certificates_issued}  variant="cert"     />
            <KpiCard label="Active Surveyors"    value={kpis?.active_surveyors}     variant="surveyor" />
          </div>
        )}
        {errors.kpis && !loading && (
          <div className="alert alert--error">KPI data unavailable — {errors.kpis}</div>
        )}

        {/* ── Under objection callout (Student 2 integration) ── */}
        {!loading && byStatus && underObjectionCount > 0 && (
          <div className="ad-objection-callout">
            <span className="ad-objection-callout__count">{underObjectionCount}</span>
            <div>
              <strong>Application{underObjectionCount !== 1 ? 's' : ''} under objection</strong>
              <p>
                Objection documents and review status are managed in{' '}
                <button className="ad-link-btn" onClick={() => navigate('/staff/registrar-review')}>
                  Registrar Review
                </button>
                {' '}and{' '}
                <button className="ad-link-btn" onClick={() => navigate('/staff/applications')}>
                  Application Details
                </button>.
              </p>
            </div>
          </div>
        )}

        {/* ── Charts row: Over Time | Certs per Month ── */}
        {!loading && (
          <div className="ad-grid-2">
            <Section title="Applications Over Time" error={errors.derived}>
              {overTime && <VBarChart data={overTime} />}
              {overTime?.length === 0 && <p className="ad-empty">No time series data.</p>}
            </Section>
            <Section title="Certificates Issued per Month" error={errors.certs}>
              {certsPerMonth && <VBarChart data={certsPerMonth} />}
              {certsPerMonth?.length === 0 && <p className="ad-empty">No certificates issued yet.</p>}
            </Section>
          </div>
        )}

        {/* ── Charts row: By Status | By Zone ── */}
        {!loading && (
          <div className="ad-grid-2">
            <Section title="Applications by Status" error={errors.derived}>
              {byStatus && (
                <HBarChart
                  data={byStatus}
                  labelKey="status"
                  valueKey="count"
                  colorFn={statusColor}
                />
              )}
            </Section>
            <Section title="Pending Applications by Zone" error={errors.derived}>
              {byZoneSource === 'geofeed:pending-applications' && (
                <p className="ad-zone-source">
                  Source: <code>/analytics/geofeeds/pending-applications</code>
                </p>
              )}
              {byZoneSource === 'parcel_ref_fallback' && (
                <p className="ad-zone-source ad-zone-source--warn">
                  Geofeed unavailable — using parcel_ref fallback (may show "unknown").
                </p>
              )}
              {byZone && (
                <HBarChart data={byZone} labelKey="zone" valueKey="count" />
              )}
              {byZone?.length === 0 && (
                <p className="ad-empty">No zone data available.</p>
              )}
            </Section>
          </div>
        )}

        {/* ── Processing time ── */}
        {!loading && (
          <Section title="Average Processing Time by Application Type (days)" error={errors.pt}>
            {processingTime && (
              <HBarChart
                data={processingTime}
                labelKey="application_type"
                valueKey="average_processing_days"
                colorFn={() => '#1D4ED8'}
              />
            )}
            {processingTime?.length === 0 && (
              <p className="ad-empty">No processing time data available.</p>
            )}
          </Section>
        )}

        {/* ── Surveyor workload (Task 32) ── */}
        {!loading && (
          <Section title="Surveyor Workload" error={errors.surveyors}>
            <SurveyorWorkload data={surveyors} />
          </Section>
        )}

        {/* ── Registrar analytics ── */}
        {!loading && (
          <Section title="Registrar Analytics" error={errors.registrars}>
            <RegistrarAnalytics data={registrars} />
          </Section>
        )}

        {/* ── Delayed Applications (Task 10) ── */}
        {!loading && (
          <Section title="Delayed Applications (> 7 days pending)" error={errors.delayed}>
            <DelayedApplicationsTable data={delayedApps} />
          </Section>
        )}

        {/* ── Student 1 workflow integration note ── */}
        {!loading && (
          <div className="ad-integration-row">
            <div className="ad-integration-card ad-integration-card--green">
              <h3 className="ad-integration-card__title">Student 1 — Workflow Integration</h3>
              <p className="ad-integration-card__body">
                Survey pipeline connects to Student 1 application workflow.
                Flow: <code>survey_required → assigned → milestones → report_uploaded</code>
                → transition via <code>PATCH /applications/&#123;id&#125;/transition</code>
                (target: <code>surveyed</code> or <code>legal_review</code>).
                Existing <code>transitionApplication()</code> in staffConsoleApi is reused — not rebuilt.
              </p>
            </div>
            <div className="ad-integration-card ad-integration-card--blue">
              <h3 className="ad-integration-card__title">Student 2 — Document &amp; Objection Integration</h3>
              <p className="ad-integration-card__body">
                Document review, objection info, applicant details, and timeline are managed in
                existing Student 2 pages (ApplicationDetails, RegistrarReview).
                These sections coexist with the Student 3 survey report section in RegistrarReview.
                Data flows via existing <code>getApplicationDocuments()</code>,
                <code>getApplicationComments()</code>, and <code>getApplicationTimeline()</code>
                functions in staffConsoleApi — not rebuilt.
              </p>
            </div>
          </div>
        )}

      </div>
    </StaffLayout>
  )
}
