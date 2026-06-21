import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import StaffLayout from '../../components/StaffLayout'
import SurveyTaskCard from '../../components/SurveyTaskCard'
import { getSurveyorTasks } from '../../api/surveyApi'
import './SurveyorTasks.css'

function getSurveyorId() {
  try {
    const user = JSON.parse(localStorage.getItem('lrmis_user'))
    if (user?.role === 'surveyor' && user?.user_id) return user.user_id
  } catch {}
  return 'SURV-001'
}

const MILESTONE_ORDER = [
  'assigned', 'visit_scheduled', 'arrived_on_site',
  'survey_started', 'survey_completed', 'report_uploaded', 'registrar_reviewed',
]

export default function SurveyorTasks() {
  const navigate = useNavigate()
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [filter,  setFilter]  = useState('all') // 'all' | 'active' | 'completed'

  const surveyorId = getSurveyorId()

  useEffect(() => {
    setLoading(true)
    setError(null)
    getSurveyorTasks(surveyorId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [surveyorId])

  const tasks = data?.tasks || []

  const filtered = tasks.filter((t) => {
    if (filter === 'active')    return t.status !== 'registrar_reviewed'
    if (filter === 'completed') return t.status === 'registrar_reviewed'
    return true
  })

  const counts = {
    all: tasks.length,
    active: tasks.filter((t) => t.status !== 'registrar_reviewed').length,
    completed: tasks.filter((t) => t.status === 'registrar_reviewed').length,
  }

  return (
    <StaffLayout>
      <div className="page-container">

        {/* ── Page header ── */}
        <div className="sv-page-header">
          <div>
            <h1 className="sv-page-header__title">Surveyor Tasks</h1>
            <p className="sv-page-header__desc">
              Assigned survey tasks for surveyor{' '}
              <code className="sv-staff-id">{surveyorId}</code>
              {data && ` — ${data.total ?? tasks.length} task${tasks.length !== 1 ? 's' : ''}`}
            </p>
          </div>
          <button
            className="btn btn--outline"
            onClick={() => navigate('/staff/dashboard')}
          >
            ← Dashboard
          </button>
        </div>

        {/* ── Filter tabs ── */}
        <div className="sv-filter-tabs">
          {(['all', 'active', 'completed']).map((f) => (
            <button
              key={f}
              type="button"
              className={`sv-filter-tab${filter === f ? ' sv-filter-tab--active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
              <span className="sv-filter-tab__count">{counts[f]}</span>
            </button>
          ))}
        </div>

        {/* ── States ── */}
        {loading && (
          <div className="sv-loading">
            <div className="sv-loading__spinner" />
            <p>Loading survey tasks…</p>
          </div>
        )}

        {!loading && error && (
          <div className="alert alert--error">
            Failed to load tasks for surveyor <code>{surveyorId}</code> — {error}
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="sv-empty">
            <div className="sv-empty__icon">📋</div>
            <p className="sv-empty__text">
              {filter === 'all'
                ? `No survey tasks assigned to surveyor ${surveyorId}.`
                : `No ${filter} tasks found.`}
            </p>
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="sv-grid">
            {filtered.map((task, i) => (
              <div key={task.task_id || i} style={{ animationDelay: `${i * 0.05}s` }}>
                <SurveyTaskCard
                  task={task}
                  onOpen={(t) => navigate(`/surveyor/tasks/${t.task_id || t.application_id}`)}
                />
              </div>
            ))}
          </div>
        )}

      </div>
    </StaffLayout>
  )
}
