import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import MapPicker from '../../components/MapPicker'
import { submitApplication } from '../../api/applicationsApi'
import './SubmitApplication.css'

const DOCUMENT_OPTIONS = [
  { id: 'national_id',               label: 'National Identity Card' },
  { id: 'title_deed',                label: 'Title Deed / Land Certificate' },
  { id: 'property_map',              label: 'Property Map / Survey Plan' },
  { id: 'power_of_attorney',         label: 'Power of Attorney (if applicable)' },
  { id: 'land_survey_report',        label: 'Land Survey Report' },
  { id: 'municipality_permit',       label: 'Municipality / Authority Permit' },
  { id: 'tax_clearance_certificate', label: 'Tax Clearance Certificate' },
]

const APPLICATION_TYPES = [
  { value: 'ownership_transfer',    label: 'Ownership Transfer' },
  { value: 'land_registration',     label: 'New Land Registration' },
  { value: 'parcel_subdivision',    label: 'Parcel Subdivision' },
  { value: 'plot_merger',           label: 'Plot Merger' },
  { value: 'lease_registration',    label: 'Lease Registration' },
  { value: 'mortgage_registration', label: 'Mortgage Registration' },
]

const STEP_LABELS = [
  'App Type',
  'Applicant Info',
  'Parcel Details',
  'Map Location',
  'Documents',
]

function computeStep(form) {
  if (form.geometry) return 5
  if (form.parcelNumber && form.blockNumber) return 4
  if (form.fullName && form.nationalId) return 3
  if (form.applicationCode) return 2
  return 1
}

function StepProgress({ form }) {
  const currentStep = computeStep(form)
  return (
    <div className="step-progress">
      {STEP_LABELS.map((label, i) => {
        const n = i + 1
        const status = n < currentStep ? 'done' : n === currentStep ? 'active' : 'upcoming'
        return (
          <div key={label} className={`step-progress__item step-progress__item--${status}`}>
            <div className="step-progress__dot">
              {status === 'done' ? '✓' : n}
            </div>
            <span className="step-progress__label">{label}</span>
          </div>
        )
      })}
    </div>
  )
}

function SectionHeader({ number, title, subtitle }) {
  return (
    <div className="section-header">
      <div className="section-header__number">{number}</div>
      <div>
        <h2 className="section-header__title">{title}</h2>
        {subtitle && <p className="section-header__subtitle">{subtitle}</p>}
      </div>
    </div>
  )
}

function Field({ label, required, error, children }) {
  return (
    <div className="form-field">
      <label className={`form-label${error ? ' form-label--error' : ''}`}>
        {label}
        {required && <span className="required"> *</span>}
      </label>
      {children}
      {error && <span className="form-error">{error}</span>}
    </div>
  )
}

const INITIAL_FORM = {
  applicationCode: 'ownership_transfer',
  fullName:    '',
  nationalId:  '',
  address:     '',
  phone:       '',
  email:       '',
  parcelNumber: '',
  blockNumber:  '',
  basinNumber:  '',
  zoneId:       '',
  geometry:     null,
  selectedDocs: [],
}

export default function SubmitApplication() {
  const navigate = useNavigate()

  const [form, setForm]               = useState(INITIAL_FORM)
  const [errors, setErrors]           = useState({})
  const [submitting, setSubmitting]   = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [result, setResult]           = useState(null)

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  const toggleDoc = (docId) => {
    setForm((f) => ({
      ...f,
      selectedDocs: f.selectedDocs.includes(docId)
        ? f.selectedDocs.filter((d) => d !== docId)
        : [...f.selectedDocs, docId],
    }))
  }

  const onGeometryChange = (geojson) => {
    setForm((f) => ({ ...f, geometry: geojson }))
    if (geojson) setErrors((e) => ({ ...e, geometry: undefined }))
  }

  const validate = () => {
    const e = {}
    if (!form.fullName.trim())     e.fullName    = 'Full name is required'
    if (!form.nationalId.trim())   e.nationalId  = 'National ID is required'
    if (!form.parcelNumber.trim()) e.parcelNumber = 'Parcel number is required'
    if (!form.blockNumber.trim())  e.blockNumber  = 'Block number is required'
    if (!form.basinNumber.trim())  e.basinNumber  = 'Basin number is required'
    if (!form.zoneId.trim())       e.zoneId       = 'Zone ID is required'
    if (!form.geometry)            e.geometry     = 'Please select and confirm a parcel location on the map'
    return e
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitError(null)

    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      const firstErrEl = document.querySelector('[data-error-anchor]')
      if (firstErrEl) firstErrEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
    setErrors({})

    const payload = {
      applicant_ref: form.nationalId.trim(),
      parcel_ref: {
        parcel_number:     form.parcelNumber.trim(),
        block_number:      form.blockNumber.trim(),
        basin_number:      form.basinNumber.trim(),
        zone_id:           form.zoneId.trim(),
        geometry:          form.geometry,
        applicant_name:    form.fullName.trim(),
        applicant_phone:   form.phone.trim(),
        applicant_email:   form.email.trim(),
        applicant_address: form.address.trim(),
        application_type:  form.applicationCode,
      },
      required_documents: form.selectedDocs,
    }

    setSubmitting(true)
    try {
      const response = await submitApplication(payload)
      setResult(response)
      navigate('/applicant/confirmation', { state: { application: response }, replace: true })
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  // ── Success fallback (if navigation didn't happen) ──
  if (result) {
    return (
      <Layout>
        <div className="submit-success">
          <div className="submit-success__card">
            <div className="submit-success__icon"><span>✓</span></div>
            <h1 className="submit-success__title">Application Submitted</h1>
            <p className="submit-success__desc">
              Your land registration application has been received and is under review.
            </p>
            <div className="submit-success__id-box">
              <div className="submit-success__id-label">Application ID</div>
              <div className="submit-success__id-value">{result.application_id}</div>
            </div>
            <p className="submit-success__hint">Keep this ID to track your application status.</p>
            <div className="submit-success__actions">
              <button className="btn btn--primary" onClick={() => navigate('/applicant')}>
                Back to Dashboard
              </button>
              <button
                className="btn btn--outline"
                onClick={() => navigate(`/applicant/track/${result.application_id}`)}
              >
                Track Application
              </button>
            </div>
          </div>
        </div>
      </Layout>
    )
  }

  // ── Form ──
  return (
    <Layout>
      <div className="page-container page-container--md">
        <div className="page-header">
          <h1>Submit Land Application</h1>
          <p>Complete all sections below and confirm your parcel location on the map.</p>
        </div>

        <StepProgress form={form} />

        <form className="submit-form" onSubmit={handleSubmit} noValidate>

          {/* Section 1: Application Type */}
          <div className="card">
            <SectionHeader number="1" title="Application Type" subtitle="Select the type of land registration application" />
            <Field label="Application Type" required>
              <select className="form-input" value={form.applicationCode} onChange={set('applicationCode')}>
                {APPLICATION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </Field>
          </div>

          {/* Section 2: Applicant Information */}
          <div className="card">
            <SectionHeader number="2" title="Applicant Information" subtitle="Enter the details of the person or entity submitting this application" />
            <div className="form-stack">
              <div className="form-grid-2">
                <Field label="Full Name" required error={errors.fullName}>
                  <input
                    data-error-anchor={errors.fullName ? '' : undefined}
                    type="text"
                    placeholder="e.g. Mohammad Al-Amin"
                    value={form.fullName}
                    onChange={set('fullName')}
                    className={`form-input${errors.fullName ? ' form-input--error' : ''}`}
                  />
                </Field>
                <Field label="National ID" required error={errors.nationalId}>
                  <input
                    data-error-anchor={errors.nationalId ? '' : undefined}
                    type="text"
                    placeholder="e.g. 123456789"
                    value={form.nationalId}
                    onChange={set('nationalId')}
                    className={`form-input${errors.nationalId ? ' form-input--error' : ''}`}
                  />
                </Field>
              </div>
              <Field label="Address">
                <input
                  type="text"
                  placeholder="City, district, street"
                  value={form.address}
                  onChange={set('address')}
                  className="form-input"
                />
              </Field>
              <div className="form-grid-2">
                <Field label="Phone Number">
                  <input
                    type="tel"
                    placeholder="+970 59X XXX XXX"
                    value={form.phone}
                    onChange={set('phone')}
                    className="form-input"
                  />
                </Field>
                <Field label="Email Address">
                  <input
                    type="email"
                    placeholder="applicant@example.com"
                    value={form.email}
                    onChange={set('email')}
                    className="form-input"
                  />
                </Field>
              </div>
            </div>
          </div>

          {/* Section 3: Parcel Information */}
          <div className="card">
            <SectionHeader number="3" title="Parcel Information" subtitle="Enter the land parcel identifiers as registered in the land registry" />
            <div className="form-grid-2">
              <Field label="Parcel Number" required error={errors.parcelNumber}>
                <input
                  data-error-anchor={errors.parcelNumber ? '' : undefined}
                  type="text"
                  placeholder="e.g. 125"
                  value={form.parcelNumber}
                  onChange={set('parcelNumber')}
                  className={`form-input${errors.parcelNumber ? ' form-input--error' : ''}`}
                />
              </Field>
              <Field label="Block Number" required error={errors.blockNumber}>
                <input
                  data-error-anchor={errors.blockNumber ? '' : undefined}
                  type="text"
                  placeholder="e.g. 7"
                  value={form.blockNumber}
                  onChange={set('blockNumber')}
                  className={`form-input${errors.blockNumber ? ' form-input--error' : ''}`}
                />
              </Field>
              <Field label="Basin Number" required error={errors.basinNumber}>
                <input
                  data-error-anchor={errors.basinNumber ? '' : undefined}
                  type="text"
                  placeholder="e.g. 3"
                  value={form.basinNumber}
                  onChange={set('basinNumber')}
                  className={`form-input${errors.basinNumber ? ' form-input--error' : ''}`}
                />
              </Field>
              <Field label="Zone ID" required error={errors.zoneId}>
                <input
                  data-error-anchor={errors.zoneId ? '' : undefined}
                  type="text"
                  placeholder="e.g. ZONE-A1"
                  value={form.zoneId}
                  onChange={set('zoneId')}
                  className={`form-input${errors.zoneId ? ' form-input--error' : ''}`}
                />
              </Field>
            </div>
          </div>

          {/* Section 4: Map Location */}
          <div className="card">
            <SectionHeader number="4" title="Parcel Location on Map" subtitle="Click on the map to mark the parcel vertices, then click Confirm Location" />
            {errors.geometry && (
              <div data-error-anchor="" className="map-error">{errors.geometry}</div>
            )}
            <MapPicker onGeometryChange={onGeometryChange} />
            {form.geometry && (
              <p className="map-confirm-text">
                Location confirmed — {form.geometry.coordinates[0].length - 1} vertices
              </p>
            )}
          </div>

          {/* Section 5: Required Documents */}
          <div className="card">
            <SectionHeader
              number="5"
              title="Required Documents"
              subtitle="Select all documents you will provide. Actual file upload is handled separately after submission."
            />
            <div className="doc-list">
              {DOCUMENT_OPTIONS.map((doc) => {
                const checked = form.selectedDocs.includes(doc.id)
                return (
                  <label key={doc.id} className={`doc-item${checked ? ' doc-item--checked' : ''}`}>
                    <input
                      type="checkbox"
                      className="doc-item__checkbox"
                      checked={checked}
                      onChange={() => toggleDoc(doc.id)}
                    />
                    <span className="doc-item__label">{doc.label}</span>
                  </label>
                )
              })}
            </div>
            {form.selectedDocs.length > 0 && (
              <p className="doc-count-hint">
                {form.selectedDocs.length} document{form.selectedDocs.length !== 1 ? 's' : ''} selected
              </p>
            )}
          </div>

          {/* Section 6: Submit */}
          {submitError && (
            <div className="alert alert--error">
              Submission failed: {submitError}
            </div>
          )}

          <div className="submit-bar">
            <div>
              <h3 className="submit-bar__title">Ready to submit?</h3>
              <p className="submit-bar__hint">Review all sections above before submitting your application.</p>
            </div>
            <button type="submit" className="btn--accent" disabled={submitting}>
              {submitting ? 'Submitting…' : 'Submit Application →'}
            </button>
          </div>

        </form>
      </div>
    </Layout>
  )
}
