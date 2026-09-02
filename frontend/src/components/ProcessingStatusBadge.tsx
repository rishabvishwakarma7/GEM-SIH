import { CheckCircle2, XCircle, Loader2, FileText, FileCheck2, CircleDashed } from 'lucide-react'
import type { ProcessingStatus } from '../types'
import { PROCESSING_STATUS_LABELS } from '../types'
import StatusBadge from './ui/StatusBadge'
import type { Tone } from './ui/Badge'

const TONE: Record<ProcessingStatus, Tone> = {
  pending: 'neutral',
  uploaded: 'info',
  extracting_text: 'warning',
  text_extracted: 'info',
  extracting_requirements: 'warning',
  completed: 'success',
  failed: 'danger',
}

const SPIN = <Loader2 className="h-3.5 w-3.5 animate-spin" />

const ICON: Record<ProcessingStatus, JSX.Element> = {
  pending: <CircleDashed className="h-3.5 w-3.5" />,
  uploaded: <FileText className="h-3.5 w-3.5" />,
  extracting_text: SPIN,
  text_extracted: <FileCheck2 className="h-3.5 w-3.5" />,
  extracting_requirements: SPIN,
  completed: <CheckCircle2 className="h-3.5 w-3.5" />,
  failed: <XCircle className="h-3.5 w-3.5" />,
}

export default function ProcessingStatusBadge({ status }: { status: ProcessingStatus }) {
  return (
    <StatusBadge tone={TONE[status]} icon={ICON[status]}>
      {PROCESSING_STATUS_LABELS[status]}
    </StatusBadge>
  )
}
