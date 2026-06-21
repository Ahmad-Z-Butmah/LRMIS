import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import StaffLayout from '../../components/StaffLayout'
import {
  getApplications,
  getApplicantById,
  generateCertificate,
} from '../../api/staffConsoleApi'
import './CertificateIssuance.css'

const ACTOR_ID = 'staff_console'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

function formatDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function parcelLabel(ref) {
  if (!ref) return '—'
  if (typeof ref === 'string') return ref
  return ref.parcel_number || '—'
}

function zoneLabel(ref) {
  if (!ref || typeof ref === 'string') return '—'
  return ref.zone_id || '—'
}

function certStatusLabel(s) {
  if (!s) return 'Not yet issued'
  return String(s).replace(/_/g, ' ')
}

export default function CertificateIssuance() {
  const navigate = useNavigate()

  const [apps, setApps]           = useState([])
  const [loading, setLoading]     = useState(true)
  const [pageError, setPageError] = useState(null)
  const [names, setNames]         = useState({})

  const [modal, setModal]         = useState(null)
  const [certResult, setCertResult] = useState(null)

  const [certType,     setCertType]     = useState('ownership')
  const [certFullName, setCertFullName] = useState('')
  const [certNatId,    setCertNatId]    = useState('')
  const [certAddress,  setCertAddress]  = useState('')
  const [certIssuedBy, setCertIssuedBy] = useState('')
  const [certErr,      setCertErr]      = useState(null)
  const [certBusy,     setCertBusy]     = useState(false)

  const loadApps = useCallback(() => {
    setLoading(true)
    setPageError(null)
    async function fetchAll() {
      const first = await getApplications({ status: 'approved', limit: 100, page: 1 })
      const items = [...(first.items || [])]
      const totalPages = first.total > 0 ? Math.ceil(first.total / 100) : 1
      if (totalPages > 1) {
        const extras = await Promise.all(
          Array.from({ length: totalPages - 1 }, (_, i) =>
            getApplications({ status: 'approved', limit: 100, page: i + 2 })
          )
        )
        extras.forEach((r) => items.push(...(r.items || [])))
      }
      return items
    }
    fetchAll()
      .then((items) => {
        setApps(items)
        const ids = [...new Set(items.map((a) => a.applicant_ref).filter(Boolean))]
        Promise.allSettled(ids.map((id) => getApplicantById(id))).then((results) => {
          const map = {}
          results.forEach((r, i) => {
            if (r.status === 'fulfilled') {
              const a = r.value
              map[ids[i]] = a.full_name || ids[i]
            }
          })
          setNames(map)
        })
      })
      .catch((e) => setPageError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadApps() }, [loadApps])

  const openCertModal = (app) => {
    setModal(app)
    setCertResult(null)
    setCertErr(null)
    const name = names[app.applicant_ref] || ''
    setCertType('ownership')
    setCertFullName(name)
    setCertNatId('')
    setCertAddress('')
    setCertIssuedBy('')
  }

  const closeModal = () => {
    setModal(null)
    setCertResult(null)
    setCertErr(null)
    setCertType('ownership')
    setCertFullName('')
    setCertNatId('')
    setCertAddress('')
    setCertIssuedBy('')
    setCertBusy(false)
  }

  const handleCertSubmit = async (e) => {
    e.preventDefault()
    if (!certFullName.trim() || !certNatId.trim() || !certAddress.trim()) return
    setCertBusy(true)
    setCertErr(null)
    try {
      const result = await generateCertificate(modal.application_id, {
        certificate_type: certType,
        issued_to: {
          full_name:   certFullName.trim(),
          national_id: certNatId.trim(),
          address:     certAddress.trim(),
        },
        issued_by: certIssuedBy.trim() || ACTOR_ID,
      })
      setCertResult(result)
      loadApps()
    } catch (err) {
      setCertErr(err.message)
    } finally {
      setCertBusy(false)
    }
  }

  return (
    <StaffLayout>
      <div className="page-container">

        <div className="ci-page-header">
          <div>
            <h1 className="ci-page-header__title">Certificate Issuance</h1>
            <p className="ci-page-header__desc">
              {loading
                ? 'Loading…'
                : `${apps.length} approved application${apps.length !== 1 ? 's' : ''} ready for certificate issuance`}
            </p>
          </div>
          <button className="btn btn--outline" onClick={() => navigate('/staff/dashboard')}>
            ← Dashboard
          </button>
        </div>

        {pageError && <div className="alert alert--error">{pageError}</div>}

        <div className="card ci-table-card">
          {loading && (
            <div className="ci-loading">Loading approved applications…</div>
          )}

          {!loading && apps.length === 0 && !pageError && (
            <div className="ci-empty">
              <div className="ci-empty__icon">📜</div>
              <p>No approved applications awaiting certificate issuance.</p>
            </div>
          )}

          {!loading && apps.length > 0 && (
            <div className="ci-table-scroll">
              <table className="ci-table">
                <thead>
                  <tr>
                    <th>Application ID</th>
                    <th>Applicant Name</th>
                    <th>Parcel</th>
                    <th>Zone</th>
                    <th>Approved Date</th>
                    <th>Certificate Status</th>
                    <th>Generate Certificate</th>
                  </tr>
                </thead>
                <tbody>
                  {apps.map((app) => (
                    <tr key={app.application_id}>
                      <td>
                        <code className="ci-app-id">{app.application_id}</code>
                      </td>
                      <td className="ci-td-muted">
                        {names[app.applicant_ref] || app.applicant_ref || '—'}
                      </td>
                      <td className="ci-td-muted">{parcelLabel(app.parcel_ref)}</td>
                      <td className="ci-td-muted">{zoneLabel(app.parcel_ref)}</td>
                      <td className="ci-td-muted">
                        {formatDate(app.updated_at || app.submitted_at)}
                      </td>
                      <td>
                        <span className="ci-cert-status">
                          Not yet issued
                        </span>
                      </td>
                      <td>
                        <div className="ci-actions">
                          <button
                            className="ci-btn ci-btn--view"
                            onClick={() => navigate(`/staff/applications/${app.application_id}`)}
                          >
                            Details
                          </button>
                          <button
                            className="ci-btn ci-btn--generate"
                            onClick={() => openCertModal(app)}
                          >
                            Generate
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>

      {/* ── Certificate modal ── */}
      {modal && (
        <div className="ci-overlay" onClick={!certResult ? closeModal : undefined}>
          <div className="ci-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ci-modal__header">
              <h3 className="ci-modal__title">
                {certResult ? 'Certificate Issued' : 'Generate Certificate'}
              </h3>
              <button className="ci-modal__close" type="button" onClick={closeModal}>×</button>
            </div>

            {certResult ? (
              <div className="ci-modal__body">
                <div className="ci-result">
                  <div className="ci-result__icon">✓</div>
                  <p className="ci-result__msg">Certificate successfully issued.</p>
                  <div className="ci-result__grid">
                    <div className="ci-result__row">
                      <span className="ci-result__label">Certificate ID</span>
                      <code className="ci-result__val">{certResult.certificate_id || '—'}</code>
                    </div>
                    <div className="ci-result__row">
                      <span className="ci-result__label">Status</span>
                      <span className="ci-result__val">{certResult.status || '—'}</span>
                    </div>
                    <div className="ci-result__row">
                      <span className="ci-result__label">Certificate Type</span>
                      <span className="ci-result__val">{certResult.certificate_type || '—'}</span>
                    </div>
                    <div className="ci-result__row">
                      <span className="ci-result__label">Issued At</span>
                      <span className="ci-result__val">{formatDateTime(certResult.issued_at)}</span>
                    </div>
                    <div className="ci-result__row">
                      <span className="ci-result__label">Issued By</span>
                      <span className="ci-result__val">{certResult.issued_by || '—'}</span>
                    </div>
                    <div className="ci-result__row">
                      <span className="ci-result__label">Applicant Ref</span>
                      <span className="ci-result__val">{certResult.applicant_ref || '—'}</span>
                    </div>
                    <div className="ci-result__row">
                      <span className="ci-result__label">Parcel ID</span>
                      <span className="ci-result__val">{certResult.parcel_id || '—'}</span>
                    </div>
                    {certResult.qr_code_url && (
                      <div className="ci-result__row">
                        <span className="ci-result__label">QR / Verification URL</span>
                        <a
                          className="ci-result__val ci-result__link"
                          href={certResult.qr_code_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {certResult.qr_code_url}
                        </a>
                      </div>
                    )}
                    {certResult.digital_signature_stub && (
                      <div className="ci-result__row">
                        <span className="ci-result__label">Digital Signature</span>
                        <code className="ci-result__val">{certResult.digital_signature_stub}</code>
                      </div>
                    )}
                  </div>
                  <p className="ci-result__note">
                    The application has advanced to <strong>certificate_issued</strong> and will no
                    longer appear in this list.
                  </p>
                </div>
                <div className="ci-modal__footer">
                  <button className="btn btn--primary" onClick={closeModal}>Done</button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCertSubmit}>
                <div className="ci-modal__body">
                  <p className="ci-modal-app-id">
                    Application: <code>{modal.application_id}</code>
                  </p>
                  {certErr && (
                    <div className="alert alert--error ci-modal-err">{certErr}</div>
                  )}
                  <div className="form-field">
                    <label className="form-label">
                      Certificate type <span className="ci-required">*</span>
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      required
                      value={certType}
                      onChange={(e) => setCertType(e.target.value)}
                      placeholder="ownership"
                    />
                  </div>
                  <div className="form-field">
                    <label className="form-label">
                      Issued to — Full name <span className="ci-required">*</span>
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      required
                      value={certFullName}
                      onChange={(e) => setCertFullName(e.target.value)}
                      placeholder="Full legal name"
                    />
                  </div>
                  <div className="form-field">
                    <label className="form-label">
                      Issued to — National ID <span className="ci-required">*</span>
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      required
                      value={certNatId}
                      onChange={(e) => setCertNatId(e.target.value)}
                      placeholder="National ID number"
                    />
                  </div>
                  <div className="form-field">
                    <label className="form-label">
                      Issued to — Address <span className="ci-required">*</span>
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      required
                      value={certAddress}
                      onChange={(e) => setCertAddress(e.target.value)}
                      placeholder="Legal address"
                    />
                  </div>
                  <div className="form-field">
                    <label className="form-label">Issued by (officer name)</label>
                    <input
                      type="text"
                      className="form-input"
                      value={certIssuedBy}
                      onChange={(e) => setCertIssuedBy(e.target.value)}
                      placeholder={`Defaults to "${ACTOR_ID}"`}
                    />
                  </div>
                </div>
                <div className="ci-modal__footer">
                  <button type="button" className="btn btn--muted" onClick={closeModal}>
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn--primary"
                    disabled={certBusy || !certFullName.trim() || !certNatId.trim() || !certAddress.trim()}
                  >
                    {certBusy ? 'Generating…' : 'Issue Certificate'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

    </StaffLayout>
  )
}
