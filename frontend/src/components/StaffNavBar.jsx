import React from 'react'
import { NavLink } from 'react-router-dom'
import '../styles/staff-nav.css'

const STAFF_LINKS = [
  { to: '/staff/dashboard',        label: 'Dashboard',        end: true  },
  { to: '/staff/applications',     label: 'Applications',     end: false },
  { to: '/staff/registrar-review', label: 'Registrar Review', end: false },
  { to: '/staff/certificates',     label: 'Certificates',     end: false },
  { to: '/surveyor/tasks',         label: 'Surveyor Tasks',   end: false },
  { to: '/map/live',               label: 'Live Map',         end: false },
  { to: '/analytics',             label: 'Analytics',        end: false },
]

export default function StaffNavBar() {
  return (
    <nav className="staff-nav" aria-label="Staff navigation">
      <div className="staff-nav__inner">
        <span className="staff-nav__label">Staff Console</span>
        {STAFF_LINKS.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `staff-nav__link${isActive ? ' staff-nav__link--active' : ''}`
            }
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
