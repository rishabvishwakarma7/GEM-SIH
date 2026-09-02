import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'
import type { ComplianceStatus } from '../types'
import { COMPLIANCE_STATUS_LABELS } from '../types'
import StatusBadge from './ui/StatusBadge'
import type { Tone } from './ui/Badge'

const TONE: Record<ComplianceStatus, Tone> = {
  compliant: 'success',
  non_compliant: 'danger',
  needs_review: 'warning',
}

const ICON: Record<ComplianceStatus, JSX.Element> = {
  compliant: <CheckCircle2 className="h-3.5 w-3.5" />,
  non_compliant: <XCircle className="h-3.5 w-3.5" />,
  needs_review: <AlertTriangle className="h-3.5 w-3.5" />,
}

export default function ComplianceStatusBadge({ status }: { status: ComplianceStatus }) {
  return (
    <StatusBadge tone={TONE[status]} icon={ICON[status]}>
      {COMPLIANCE_STATUS_LABELS[status]}
    </StatusBadge>
  )
}
