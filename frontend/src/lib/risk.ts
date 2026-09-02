/** Shared risk-level helpers used across multiple components. */

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export function riskColor(level: RiskLevel | string | null | undefined): string {
  switch (level) {
    case 'critical': return 'text-red-700'
    case 'high':     return 'text-orange-600'
    case 'medium':   return 'text-yellow-600'
    case 'low':      return 'text-green-600'
    default:         return 'text-slate-400'
  }
}

export function riskBg(level: RiskLevel | string | null | undefined): string {
  switch (level) {
    case 'critical': return 'bg-red-50 border-red-200'
    case 'high':     return 'bg-orange-50 border-orange-200'
    case 'medium':   return 'bg-yellow-50 border-yellow-200'
    case 'low':      return 'bg-green-50 border-green-200'
    default:         return 'bg-slate-50 border-slate-200'
  }
}

export function riskBadgeClass(level: RiskLevel | string | null | undefined): string {
  switch (level) {
    case 'critical': return 'bg-red-100 text-red-800 border border-red-200'
    case 'high':     return 'bg-orange-100 text-orange-800 border border-orange-200'
    case 'medium':   return 'bg-yellow-100 text-yellow-800 border border-yellow-200'
    case 'low':      return 'bg-green-100 text-green-800 border border-green-200'
    default:         return 'bg-slate-100 text-slate-600 border border-slate-200'
  }
}

export function riskLabel(level: RiskLevel | string | null | undefined): string {
  if (!level) return 'Unknown'
  return level.charAt(0).toUpperCase() + level.slice(1)
}

export function severityBadgeClass(severity: string): string {
  switch (severity) {
    case 'critical': return 'bg-red-100 text-red-800 border border-red-200'
    case 'high':     return 'bg-orange-100 text-orange-800 border border-orange-200'
    case 'medium':   return 'bg-yellow-100 text-yellow-800 border border-yellow-200'
    case 'low':      return 'bg-blue-100 text-blue-800 border border-blue-200'
    case 'info':     return 'bg-slate-100 text-slate-700 border border-slate-200'
    default:         return 'bg-slate-100 text-slate-600 border border-slate-200'
  }
}

export function reviewStatusBadge(status: string): string {
  switch (status) {
    case 'open':                   return 'bg-blue-100 text-blue-800'
    case 'assigned':               return 'bg-purple-100 text-purple-800'
    case 'in_review':              return 'bg-yellow-100 text-yellow-800'
    case 'escalated':              return 'bg-red-100 text-red-800'
    case 'approved':               return 'bg-green-100 text-green-800'
    case 'rejected':               return 'bg-red-100 text-red-800'
    case 'clarification_required': return 'bg-orange-100 text-orange-800'
    case 'closed':                 return 'bg-slate-100 text-slate-600'
    default:                       return 'bg-slate-100 text-slate-600'
  }
}

export function decisionBadge(decision: string): string {
  switch (decision) {
    case 'qualified':              return 'bg-green-100 text-green-800 border border-green-200'
    case 'disqualified':           return 'bg-red-100 text-red-800 border border-red-200'
    case 'clarification_required': return 'bg-yellow-100 text-yellow-800 border border-yellow-200'
    default:                       return 'bg-slate-100 text-slate-600'
  }
}
