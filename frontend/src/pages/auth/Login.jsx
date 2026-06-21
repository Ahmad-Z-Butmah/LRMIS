import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const ROLES = [
  {
    value:       'applicant',
    label:       'Applicant',
    description: 'Submit and track land registration applications',
    redirect:    '/applicant',
  },
  {
    value:       'staff',
    label:       'Staff / Registrar',
    description: 'Review applications, issue certificates, manage workflow',
    redirect:    '/staff/dashboard',
  },
  {
    value:       'surveyor',
    label:       'Surveyor',
    description: 'Manage survey tasks and field reports',
    redirect:    '/surveyor/tasks',
  },
  {
    value:       'manager',
    label:       'Manager',
    description: 'View analytics dashboard and system reports',
    redirect:    '/analytics',
  },
]

const SURVEYOR_IDS = ['SURV-001', 'SURV-002']

export default function Login() {
  const navigate = useNavigate()
  const [selectedRole, setSelectedRole] = useState('')
  const [surveyorId,   setSurveyorId]   = useState('SURV-002')

  function handleLogin() {
    if (!selectedRole) return
    const role   = ROLES.find((r) => r.value === selectedRole)
    const userId = selectedRole === 'surveyor' ? surveyorId : `demo_${role.value}`
    localStorage.setItem(
      'lrmis_user',
      JSON.stringify({
        role:         role.value,
        user_id:      userId,
        display_name: role.label,
      }),
    )
    navigate(role.redirect, { replace: true })
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>

        {/* Header */}
        <div style={styles.header}>
          <div style={styles.badge}>LRMIS</div>
          <h1 style={styles.title}>Land Registration Management</h1>
          <p style={styles.subtitle}>Select your role to continue</p>
        </div>

        {/* Role selection */}
        <div style={styles.roleGrid}>
          {ROLES.map((r) => (
            <button
              key={r.value}
              type="button"
              style={{
                ...styles.roleBtn,
                ...(selectedRole === r.value ? styles.roleBtnActive : {}),
              }}
              onClick={() => setSelectedRole(r.value)}
            >
              <span style={styles.roleLabel}>{r.label}</span>
              <span style={styles.roleDesc}>{r.description}</span>
            </button>
          ))}
        </div>

        {/* Surveyor ID picker — only shown when Surveyor role is selected */}
        {selectedRole === 'surveyor' && (
          <div style={styles.surveyorPicker}>
            <p style={styles.surveyorPickerLabel}>Select surveyor account:</p>
            <div style={styles.surveyorBtns}>
              {SURVEYOR_IDS.map((id) => (
                <button
                  key={id}
                  type="button"
                  style={{
                    ...styles.surveyorBtn,
                    ...(surveyorId === id ? styles.surveyorBtnActive : {}),
                  }}
                  onClick={() => setSurveyorId(id)}
                >
                  {id}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Enter button */}
        <button
          type="button"
          style={{
            ...styles.enterBtn,
            ...(selectedRole ? {} : styles.enterBtnDisabled),
          }}
          onClick={handleLogin}
          disabled={!selectedRole}
        >
          Enter System
        </button>

        <p style={styles.note}>
          Demo login — no password required. Role selection persists in localStorage.
        </p>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight:       '100vh',
    display:         'flex',
    alignItems:      'center',
    justifyContent:  'center',
    background:      'linear-gradient(135deg, #0D2318 0%, #15532D 60%, #1A7A45 100%)',
    padding:         '24px',
  },
  card: {
    background:   '#fff',
    borderRadius: '16px',
    boxShadow:    '0 20px 40px rgba(0,0,0,0.25)',
    padding:      '48px 40px',
    width:        '100%',
    maxWidth:     '520px',
    animation:    'card-rise 0.4s ease-out both',
  },
  header: {
    textAlign:    'center',
    marginBottom: '36px',
  },
  badge: {
    display:        'inline-block',
    background:     '#15532D',
    color:          '#FCD34D',
    fontWeight:     '800',
    fontSize:       '13px',
    letterSpacing:  '0.12em',
    padding:        '6px 16px',
    borderRadius:   '999px',
    marginBottom:   '16px',
  },
  title: {
    margin:      '0 0 8px',
    fontSize:    '24px',
    fontWeight:  '700',
    color:       '#0F172A',
    lineHeight:  '1.2',
  },
  subtitle: {
    margin:   '0',
    color:    '#64748B',
    fontSize: '15px',
  },
  roleGrid: {
    display:       'flex',
    flexDirection: 'column',
    gap:           '12px',
    marginBottom:  '28px',
  },
  roleBtn: {
    display:       'flex',
    flexDirection: 'column',
    alignItems:    'flex-start',
    gap:           '3px',
    padding:       '16px 20px',
    borderRadius:  '10px',
    border:        '2px solid #E2E8F0',
    background:    '#F7F9FC',
    cursor:        'pointer',
    textAlign:     'left',
    transition:    'border-color 0.15s, background 0.15s, box-shadow 0.15s',
  },
  roleBtnActive: {
    borderColor: '#15532D',
    background:  '#F0FDF4',
    boxShadow:   '0 0 0 3px rgba(21,83,45,0.12)',
  },
  roleLabel: {
    fontSize:   '15px',
    fontWeight: '700',
    color:      '#0F172A',
  },
  roleDesc: {
    fontSize: '13px',
    color:    '#64748B',
  },
  enterBtn: {
    width:        '100%',
    padding:      '14px 24px',
    borderRadius: '10px',
    border:       'none',
    background:   '#15532D',
    color:        '#fff',
    fontSize:     '16px',
    fontWeight:   '700',
    cursor:       'pointer',
    transition:   'background 0.15s, box-shadow 0.15s',
    marginBottom: '16px',
  },
  enterBtnDisabled: {
    background: '#94A3B8',
    cursor:     'not-allowed',
  },
  note: {
    margin:    '0',
    textAlign: 'center',
    fontSize:  '12px',
    color:     '#94A3B8',
  },
  surveyorPicker: {
    marginBottom: '20px',
    padding:      '14px 16px',
    borderRadius: '10px',
    background:   '#F0FDF4',
    border:       '1px solid #BBF7D0',
  },
  surveyorPickerLabel: {
    margin:     '0 0 10px',
    fontSize:   '12px',
    fontWeight: '700',
    color:      '#15532D',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
  },
  surveyorBtns: {
    display: 'flex',
    gap:     '10px',
  },
  surveyorBtn: {
    flex:         '1',
    padding:      '10px 16px',
    borderRadius: '8px',
    border:       '2px solid #BBF7D0',
    background:   '#fff',
    fontSize:     '14px',
    fontWeight:   '700',
    color:        '#15532D',
    cursor:       'pointer',
    transition:   'border-color 0.15s, background 0.15s',
    fontFamily:   'monospace',
  },
  surveyorBtnActive: {
    borderColor: '#15532D',
    background:  '#DCFCE7',
  },
}
