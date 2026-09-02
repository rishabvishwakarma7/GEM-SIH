import { CheckCircle2, XCircle, AlertTriangle, CircleDashed } from 'lucide-react'
import StatusBadge from './ui/StatusBadge'
import type { Tone } from './ui/Badge'

const TONE: Record<string, Tone> = {
  compliant: 'success',
  non_compliant: 'danger',
  needs_review: 'warning',
  not_evaluated: 'neutral',
}

const ICON: Record<string, JSX.Element> = {
  compliant: <CheckCircle2 className="h-3.5 w-3.5" />,
  non_compliant: <XCircle className="h-3.5 w-3.5" />,
  needs_review: <AlertTriangle className="h-3.5 w-3.5" />,
  not_evaluated: <CircleDashed className="h-3.5 w-3.5" />,
}

const LABELS: Record<string, string> = {
  compliant: 'Compliant',
  non_compliant: 'Non-Compliant',
  needs_review: 'Needs Review',
  not_evaluated: 'Not Evaluated',
}

export default function DashboardStatusPill({ status }: { status: string }) {
  const key = status in TONE ? status : 'not_evaluated'
  return (
    <StatusBadge tone={TONE[key]} icon={ICON[key]}>
      {LABELS[key]}
    </StatusBadge>
  )
}
