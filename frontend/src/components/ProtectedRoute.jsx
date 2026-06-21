import { Navigate } from 'react-router-dom'

/**
 * localStorage-based route guard (demo auth — Task 27).
 * - No user in localStorage → redirect to /login
 * - allowedRoles provided and user.role not in list → redirect to /login
 * - Otherwise → render children
 */
export default function ProtectedRoute({ children, allowedRoles }) {
  const raw = localStorage.getItem('lrmis_user')
  if (!raw) {
    return <Navigate to="/login" replace />
  }
  try {
    const user = JSON.parse(raw)
    if (allowedRoles && !allowedRoles.includes(user.role)) {
      return <Navigate to="/login" replace />
    }
    return children
  } catch {
    return <Navigate to="/login" replace />
  }
}
