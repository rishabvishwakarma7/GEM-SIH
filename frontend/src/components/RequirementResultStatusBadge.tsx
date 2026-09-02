import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'
import type { RequirementResultStatus } from '../types'
import StatusBadge from './ui/StatusBadge'
import type { Tone } from './ui/Badge'

const TONE: Record<RequirementResultStatus, Tone> = {
  COMPLIANT: 'success',
  NON_COMPLIANT: 'danger',
  NEEDS_REVIEW: 'warning',
}

const ICON: Record<RequirementResultStatus, JSX.Element> = {
  COMPLIANT: <CheckCircle2 className="h-3.5 w-3.5" />,
  NON_COMPLIANT: <XCircle className="h-3.5 w-3.5" />,
  NEEDS_REVIEW: <AlertTriangle className="h-3.5 w-3.5" />,
}

const LABELS: Record<RequirementResultStatus, string> = {
  COMPLIANT: 'Compliant',
  NON_COMPLIANT: 'Non-Compliant',
  NEEDS_REVIEW: 'Needs Review',
}

export default function RequirementResultStatusBadge({
  status,
}: {
  status: RequirementResultStatus
}) {
  return (
    <StatusBadge tone={TONE[status]} icon={ICON[status]} size="sm">
      {LABELS[status]}
    </StatusBadge>
  )
}
