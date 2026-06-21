import './SurveyMilestoneStepper.css'

const MILESTONES = [
  { key: 'assigned',           label: 'Assigned',           short: 'Assigned' },
  { key: 'visit_scheduled',    label: 'Visit Scheduled',    short: 'Scheduled' },
  { key: 'arrived_on_site',    label: 'Arrived on Site',    short: 'On Site' },
  { key: 'survey_started',     label: 'Survey Started',     short: 'Started' },
  { key: 'survey_completed',   label: 'Survey Completed',   short: 'Completed' },
  { key: 'report_uploaded',    label: 'Report Uploaded',    short: 'Uploaded' },
  { key: 'registrar_reviewed', label: 'Registrar Reviewed', short: 'Reviewed' },
]

export default function SurveyMilestoneStepper({ currentMilestone }) {
  const currentIdx = MILESTONES.findIndex((m) => m.key === currentMilestone)
  const effectiveIdx = currentIdx === -1 ? 0 : currentIdx

  return (
    <div className="sms">
      <div className="sms__track">
        {MILESTONES.map((m, i) => {
          const isCompleted = i < effectiveIdx
          const isCurrent   = i === effectiveIdx
          const isUpcoming  = i > effectiveIdx

          let stateClass = ''
          if (isCompleted) stateClass = 'sms__step--completed'
          else if (isCurrent) stateClass = 'sms__step--current'
          else stateClass = 'sms__step--upcoming'

          return (
            <div key={m.key} className={`sms__step ${stateClass}`}>
              {/* Connector line (before node, skip first) */}
              {i > 0 && (
                <div className={`sms__line${isCompleted ? ' sms__line--done' : ''}`} />
              )}
              <div className="sms__node-wrap">
                <div className="sms__node">
                  {isCompleted ? (
                    <svg viewBox="0 0 12 12" fill="none" className="sms__check">
                      <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : (
                    <span className="sms__num">{i + 1}</span>
                  )}
                </div>
                <span className="sms__label">{m.short}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Verbose current milestone label */}
      <div className="sms__current-label">
        <span className="sms__current-prefix">Current:</span>
        <span className="sms__current-value">
          {MILESTONES[effectiveIdx]?.label || currentMilestone}
        </span>
        {currentMilestone === 'registrar_reviewed' && (
          <span className="sms__final-badge">Complete</span>
        )}
      </div>
    </div>
  )
}
