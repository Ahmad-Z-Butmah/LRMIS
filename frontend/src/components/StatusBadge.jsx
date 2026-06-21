import './StatusBadge.css'

const STATUS_LABELS = {
  submitted:          'Submitted',
  pre_checked:        'Pre Checked',
  missing_documents:  'Missing Documents',
  on_hold:            'On Hold',
  survey_required:    'Survey Required',
  surveyed:           'Surveyed',
  legal_review:       'Legal Review',
  under_objection:    'Under Objection',
  approved:           'Approved',
  certificate_issued: 'Certificate Issued',
  closed:             'Closed',
  rejected:           'Rejected',
}

export default function StatusBadge({ status }) {
  const key   = status ?? 'unknown'
  const slug  = key.replace(/_/g, '-')
  const label = STATUS_LABELS[key] ?? key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  return (
    <span className={`status-badge status-badge--${slug}`}>
      {label}
    </span>
  )
}
