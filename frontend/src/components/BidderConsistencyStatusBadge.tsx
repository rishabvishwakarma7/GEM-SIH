import { CheckCircle2, XCircle, AlertTriangle, CircleDashed } from 'lucide-react'
import type { BidderConsistencyStatus } from '../types'
import { BIDDER_CONSISTENCY_STATUS_LABELS } from '../types'
import StatusBadge from './ui/StatusBadge'
import type { Tone } from './ui/Badge'

const TONE: Record<BidderConsistencyStatus, Tone> = {
  not_analyzed: 'neutral',
  consistent: 'success',
  needs_review: 'warning',
  inconsistent: 'danger',
}

const ICON: Record<BidderConsistencyStatus, JSX.Element> = {
  not_analyzed: <CircleDashed className="h-3.5 w-3.5" />,
  consistent: <CheckCircle2 className="h-3.5 w-3.5" />,
  needs_review: <AlertTriangle className="h-3.5 w-3.5" />,
  inconsistent: <XCircle className="h-3.5 w-3.5" />,
}

export default function BidderConsistencyStatusBadge({
  status,
}: {
  status: BidderConsistencyStatus
}) {
  return (
    <StatusBadge tone={TONE[status]} icon={ICON[status]}>
      {BIDDER_CONSISTENCY_STATUS_LABELS[status]}
    </StatusBadge>
  )
}
