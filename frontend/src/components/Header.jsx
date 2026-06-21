import React from 'react'
import { NavLink } from 'react-router-dom'
import '../styles/layout.css'

const APPLICANT_LINKS = [
  { to: '/applicant',                  label: 'Dashboard',           end: true },
  { to: '/applicant/submit',           label: 'Submit Application' },
  { to: '/applicant/track',            label: 'Track Application' },
  { to: '/applicant/upload-documents', label: 'Upload Documents' },
]

function getStoredRole() {
  try { return JSON.parse(localStorage.getItem('lrmis_user') || '{}').role || null } catch { return null }
}

const ROLE_HOME = {
  applicant: '/applicant',
  staff:     '/staff/dashboard',
  surveyor:  '/surveyor/tasks',
  manager:   '/analytics',
}

export default function Header() {
  const role    = getStoredRole()
  const brandTo = ROLE_HOME[role] || '/login'
  const links   = role === 'applicant' ? APPLICANT_LINKS : []

  return (
    <header className="app-header">
      <NavLink to={brandTo} className="header__brand">
        <div className="header__logo-mark">LR</div>
        <div className="header__brand-text">
          <span className="header__logo">LRMIS</span>
          <span className="header__subtitle">Land Registration Portal</span>
        </div>
      </NavLink>

      {links.length > 0 && (
        <nav className="header__nav">
          {links.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `header__nav-link${isActive ? ' header__nav-link--active' : ''}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}
