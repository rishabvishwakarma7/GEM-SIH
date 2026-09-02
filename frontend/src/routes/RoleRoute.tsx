import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../context/AuthContext'
import AuthSplash from '../components/AuthSplash'
import Unauthorized from '../pages/Unauthorized'
import type { UserRole } from '../types'

interface RoleRouteProps {
  roles: UserRole[]
  children: ReactNode
}

/**
 * Route guard combining authentication + role authorization.
 *  - Session resolving  → branded splash
 *  - Not authenticated  → redirect to /login
 *  - Wrong role         → in-shell 403 page (URL preserved)
 *  - Authorized         → render children
 *
 * NOTE: This is defense-in-depth for UX only. The backend independently
 * enforces the same authorization with require_roles(...) and returns HTTP 403
 * regardless of what the client renders or what is stored in localStorage.
 */
export default function RoleRoute({ roles, children }: RoleRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <AuthSplash />
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (!roles.includes(user.role)) {
    return <Unauthorized />
  }

  return <>{children}</>
}
