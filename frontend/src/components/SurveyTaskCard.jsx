import './SurveyTaskCard.css'

const MILESTONE_LABELS = {
  assigned:           'Assigned',
  visit_scheduled:    'Visit Scheduled',
  arrived_on_site:    'Arrived on Site',
  survey_started:     'Survey Started',
  survey_completed:   'Survey Completed',
  report_uploaded:    'Report Uploaded',
  registrar_reviewed: 'Registrar Reviewed',
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

export default function SurveyTaskCard({ task = {}, onOpen }) {
  const milestone = task.current_milestone || task.status || 'assigned'
  const priority  = (task.priority || 'medium').toLowerCase()

  return (
    <div className={`stc stc--priority-${priority}`}>
      <div className="stc__head">
        <code className="stc__task-id">{task.task_id || '—'}</code>
        <div className="stc__badges">
          {task.report_uploaded && (
            <span className="stc__badge stc__badge--report">Report Uploaded</span>
          )}
          <span className={`stc__badge stc__badge--priority stc__badge--${priority}`}>
            {priority.toUpperCase()}
          </span>
        </div>
      </div>

      <div className="stc__grid">
        <div className="stc__field">
          <span className="stc__field-label">Application</span>
          <code className="stc__field-value stc__app-id">{task.application_id || '—'}</code>
        </div>
        <div className="stc__field">
          <span className="stc__field-label">Parcel No.</span>
          <span className="stc__field-value">{task.parcel_number || '—'}</span>
        </div>
        <div className="stc__field">
          <span className="stc__field-label">Zone</span>
          <span className="stc__field-value">{task.zone || '—'}</span>
        </div>
        <div className="stc__field">
          <span className="stc__field-label">Scheduled Visit</span>
          <span className="stc__field-value">{formatDate(task.scheduled_visit_date)}</span>
        </div>
      </div>

      <div className="stc__milestone-row">
        <span className="stc__milestone-label">Milestone</span>
        <span className={`stc__milestone-badge stc__milestone-badge--${milestone}`}>
          {MILESTONE_LABELS[milestone] || milestone.replace(/_/g, ' ')}
        </span>
      </div>

      {onOpen && (
        <div className="stc__footer">
          <button className="stc__open-btn" onClick={() => onOpen(task)} type="button">
            Open Task →
          </button>
        </div>
      )}
    </div>
  )
}
