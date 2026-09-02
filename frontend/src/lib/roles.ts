import type { User, UserRole } from '../types'

/** True when the user exists and holds one of the given roles. */
export function hasRole(user: User | null | undefined, ...roles: UserRole[]): boolean {
  return !!user && roles.includes(user.role)
}

/** Full administrative access (user management, roles, settings). */
export const isAdmin = (user: User | null | undefined): boolean => hasRole(user, 'admin')

/**
 * Can perform evaluation actions that mutate data: create tenders/bidders,
 * upload & process documents, run verification, evaluate compliance,
 * generate reports. Mirrors the backend's require_roles(ADMIN, EVALUATOR).
 */
export const canManage = (user: User | null | undefined): boolean =>
  hasRole(user, 'admin', 'evaluator')

/** Can view the audit trail. Mirrors backend require_roles(ADMIN, EVALUATOR). */
export const canViewAudit = (user: User | null | undefined): boolean =>
  hasRole(user, 'admin', 'evaluator')

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrator',
  evaluator: 'Evaluator',
  viewer: 'Viewer',
}

export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  admin:
    'Full platform access including user management, role assignment and system settings.',
  evaluator:
    'Can create and manage tenders and bidders, run AI verification, evaluate compliance and generate reports.',
  viewer:
    'Read-only access to tenders, bidders, compliance results and reports.',
}
