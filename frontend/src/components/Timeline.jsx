import React from 'react'
import StatusBadge from './StatusBadge'
import './Timeline.css'

// Ordered main workflow steps
const MAIN_WORKFLOW = [
  { key: 'submitted',          label: 'Submitted',          sub: 'Application received by registry' },
  { key: 'pre_checked',        label: 'Pre Checked',        sub: 'Initial review completed' },
  { key: 'survey_required',    label: 'Survey Required',    sub: 'Land survey requested' },
  { key: 'surveyed',           label: 'Surveyed',           sub: 'Survey report received' },
  { key: 'legal_review',       label: 'Legal Review',       sub: 'Under legal examination' },
  { key: 'approved',           label: 'Approved',           sub: 'Application approved' },
  { key: 'certificate_issued', label: 'Certificate Issued', sub: 'Registration certificate ready' },
]

// Alternative statuses shown as special banners, not stepper steps
const ALT_BANNERS = {
  missing_documents: {
    type: 'warning',
    icon: '⚠️',
    title: 'Missing Documents',
    desc: 'The application is paused — required documents must be uploaded to continue processing.',
  },
  on_hold: {
    type: 'warning',
    icon: '⏸️',
    title: 'On Hold',
    desc: 'The application has been temporarily placed on hold. Contact the registry office for details.',
  },
  under_objection: {
    type: 'danger',
    icon: '📩',
    title: 'Under Objection',
    desc: 'A formal objection has been filed against this application and is currently under review.',
  },
  rejected: {
    type: 'danger',
    icon: '❌',
    title: 'Rejected',
    desc: 'This application has been rejected. Please visit the registry office for further guidance.',
  },
  closed: {
    type: 'neutral',
    icon: '🔒',
    title: 'Closed',
    desc: 'This application has been closed.',
  },
}

function formatDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function Timeline({
  currentStatus,
  auditTimeline,
  events,         // backward-compat alias for auditTimeline
}) {
  const eventLog   = auditTimeline ?? events ?? []
  const mainIdx    = MAIN_WORKFLOW.findIndex((s) => s.key === currentStatus)
  const isAltState = currentStatus && mainIdx === -1
  const altBanner  = isAltState ? ALT_BANNERS[currentStatus] : null

  // For alt states: scan events to find how far along the main workflow we got
  const lastPassedMainIdx = MAIN_WORKFLOW.reduce((max, step, i) => {
    const seen = eventLog.some((e) => e.state === step.key)
    return seen ? i : max
  }, -1)

  if (!currentStatus && !eventLog.length) {
    return (
      <div className="timeline-empty">
        <div className="timeline-empty__icon">📅</div>
        <p className="timeline-empty__text">No timeline data available yet.</p>
      </div>
    )
  }

  return (
    <div className="timeline-wrapper">

      {/* ── Workflow progress stepper ── */}
      {currentStatus && (
        <section className="timeline-progress">
          <p className="timeline-section-title">Workflow Progress</p>
          <div className="timeline-steps">
            {MAIN_WORKFLOW.map((step, i) => {
              let stepStatus
              if (mainIdx !== -1) {
                // currentStatus is in the main workflow
                if (i < mainIdx)      stepStatus = 'completed'
                else if (i === mainIdx) stepStatus = 'current'
                else                  stepStatus = 'upcoming'
              } else {
                // currentStatus is an alt state — infer progress from event log
                stepStatus = i <= lastPassedMainIdx ? 'completed' : 'upcoming'
              }

              const isLast = i === MAIN_WORKFLOW.length - 1
              return (
                <div key={step.key} className={`timeline-step timeline-step--${stepStatus}`}>
                  <div className="timeline-step__rail">
                    <div className="timeline-step__dot">
                      {stepStatus === 'completed' && (
                        <span className="timeline-step__check">✓</span>
                      )}
                    </div>
                    {!isLast && <div className="timeline-step__line" />}
                  </div>
                  <div className="timeline-step__body">
                    <div className="timeline-step__label">{step.label}</div>
                    <div className="timeline-step__sub">{step.sub}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* ── Alternative state banner ── */}
      {altBanner && (
        <div className={`timeline-alt-banner timeline-alt-banner--${altBanner.type}`}>
          <span className="timeline-alt-banner__icon">{altBanner.icon}</span>
          <div>
            <strong className="timeline-alt-banner__title">{altBanner.title}</strong>
            <p className="timeline-alt-banner__desc">{altBanner.desc}</p>
          </div>
        </div>
      )}

      {/* ── Audit event log ── */}
      {eventLog.length > 0 && (
        <section className="timeline-log">
          <p className="timeline-section-title">Event History</p>
          <div className="timeline-log__list">
            {eventLog.map((ev, i) => {
              const isLast = i === eventLog.length - 1
              const dotSlug = (ev.state || 'unknown').replace(/_/g, '-')
              return (
                <div key={i} className={`timeline-log__item${isLast ? ' timeline-log__item--last' : ''}`}>
                  <div className="timeline-log__rail">
                    <div className={`timeline-log__dot timeline-log__dot--${dotSlug}`} />
                    {!isLast && <div className="timeline-log__line" />}
                  </div>
                  <div className="timeline-log__content">
                    <div className="timeline-log__header">
                      <StatusBadge status={ev.state} />
                      <span className="timeline-log__time">{formatDateTime(ev.timestamp)}</span>
                    </div>
                    {ev.action && <div className="timeline-log__action">{ev.action}</div>}
                    {ev.performed_by && (
                      <div className="timeline-log__actor">by {ev.performed_by}</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {currentStatus && !eventLog.length && (
        <p className="timeline-log__empty">No detailed history recorded yet.</p>
      )}
    </div>
  )
}
