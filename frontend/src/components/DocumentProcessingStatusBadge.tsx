import { CheckCircle2, XCircle, Loader2, FileText, FileCheck2 } from 'lucide-react'
import type { DocumentProcessingStatus } from '../types'
import { DOCUMENT_PROCESSING_STATUS_LABELS } from '../types'
import StatusBadge from './ui/StatusBadge'
import type { Tone } from './ui/Badge'

const TONE: Record<DocumentProcessingStatus, Tone> = {
  uploaded: 'info',
  extracting_text: 'warning',
  text_extracted: 'info',
  extracting_data: 'warning',
  completed: 'success',
  failed: 'danger',
}

const SPIN = <Loader2 className="h-3.5 w-3.5 animate-spin" />

const ICON: Record<DocumentProcessingStatus, JSX.Element> = {
  uploaded: <FileText className="h-3.5 w-3.5" />,
  extracting_text: SPIN,
  text_extracted: <FileCheck2 className="h-3.5 w-3.5" />,
  extracting_data: SPIN,
  completed: <CheckCircle2 className="h-3.5 w-3.5" />,
  failed: <XCircle className="h-3.5 w-3.5" />,
}

export default function DocumentProcessingStatusBadge({
  status,
}: {
  status: DocumentProcessingStatus
}) {
  return (
    <StatusBadge tone={TONE[status]} icon={ICON[status]}>
      {DOCUMENT_PROCESSING_STATUS_LABELS[status]}
    </StatusBadge>
  )
}
