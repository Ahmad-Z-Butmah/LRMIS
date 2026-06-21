import './MapFilters.css'

export default function MapFilters({ filters = {}, onChange, counts = {} }) {
  function toggle(key) {
    onChange({ ...filters, [key]: !filters[key] })
  }

  function setField(key, value) {
    onChange({ ...filters, [key]: value })
  }

  const LAYER_TOGGLES = [
    { key: 'showParcels',       label: 'Parcels',             color: '#15532D', count: counts.parcels },
    { key: 'showPending',       label: 'Pending Applications', color: '#D97706', count: counts.pending },
    { key: 'showSurveyRequired',label: 'Survey Required',      color: '#F59E0B', count: counts.surveyRequired },
    { key: 'showDisputed',      label: 'Disputed Parcels',     color: '#DC2626', count: counts.disputed },
    { key: 'showSurveyTasks',   label: 'Survey Tasks',         color: '#1D4ED8', count: counts.surveyTasks },
    { key: 'showHeatmap',       label: 'Pending Heatmap',      color: '#7C3AED', count: counts.heatmap },
  ]

  return (
    <div className="mf">
      <div className="mf__header">
        <span className="mf__title">Map Layers</span>
      </div>

      {/* ── Layer toggles ── */}
      <div className="mf__section">
        <p className="mf__section-label">Visible Layers</p>
        <div className="mf__layers">
          {LAYER_TOGGLES.map(({ key, label, color, count }) => (
            <button
              key={key}
              type="button"
              className={`mf__layer-btn${filters[key] ? ' mf__layer-btn--on' : ''}`}
              onClick={() => toggle(key)}
            >
              <span className="mf__layer-dot" style={{ background: filters[key] ? color : 'var(--color-border)' }} />
              <span className="mf__layer-label">{label}</span>
              {count !== undefined && (
                <span className="mf__layer-count">{count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ── Zone filter ── */}
      <div className="mf__section">
        <p className="mf__section-label">Filter by Zone</p>
        <input
          type="text"
          className="mf__input"
          placeholder="Zone ID (e.g. Z-WEST)"
          value={filters.zone || ''}
          onChange={(e) => setField('zone', e.target.value)}
        />
      </div>

      {/* ── Application type filter ── */}
      <div className="mf__section">
        <p className="mf__section-label">Application Type</p>
        <select
          className="mf__select"
          value={filters.applicationType || ''}
          onChange={(e) => setField('applicationType', e.target.value)}
        >
          <option value="">All Types</option>
          <option value="ownership">Ownership</option>
          <option value="first_registration">First Registration</option>
          <option value="ownership_transfer">Ownership Transfer</option>
          <option value="subdivision">Subdivision</option>
          <option value="inheritance">Inheritance</option>
          <option value="lease_registration">Lease Registration</option>
        </select>
      </div>

      {/* ── Status filter ── */}
      <div className="mf__section">
        <p className="mf__section-label">Filter by Status</p>
        <select
          className="mf__select"
          value={filters.status || ''}
          onChange={(e) => setField('status', e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="submitted">Submitted</option>
          <option value="pre_checked">Pre Checked</option>
          <option value="survey_required">Survey Required</option>
          <option value="missing_documents">Missing Documents</option>
          <option value="under_objection">Under Objection</option>
        </select>
      </div>

      {/* ── Dispute filter ── */}
      <div className="mf__section">
        <p className="mf__section-label">Dispute State</p>
        <select
          className="mf__select"
          value={filters.disputeState || ''}
          onChange={(e) => setField('disputeState', e.target.value)}
        >
          <option value="">All</option>
          <option value="disputed">Disputed Only</option>
          <option value="none">No Dispute</option>
        </select>
      </div>

      {/* ── Reset ── */}
      <button
        type="button"
        className="mf__reset-btn"
        onClick={() => onChange({
          showParcels: true,
          showPending: true,
          showSurveyRequired: true,
          showDisputed: true,
          showSurveyTasks: true,
          showHeatmap: false,
          zone: '',
          applicationType: '',
          status: '',
          disputeState: '',
        })}
      >
        Reset Filters
      </button>
    </div>
  )
}
