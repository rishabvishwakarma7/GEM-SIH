import { AlertTriangle } from 'lucide-react'
import Badge from './ui/Badge'
import type { Tone } from './ui/Badge'

interface Props {
  confidence?: number | null
  needsReview: boolean
}

/**
 * Shows an AI extraction/verification confidence as a percentage. Because the
 * platform is AI-assisted (not authoritative), a low score or an explicit
 * review flag is surfaced with a warning icon so evaluators verify manually.
 */
export default function ConfidenceIndicator({ confidence, needsReview }: Props) {
  if (confidence === null || confidence === undefined) {
    return (
      <Badge tone="neutral" title="No confidence score available">
        No score
      </Badge>
    )
  }

  const pct = Math.round(confidence * 100)
  let tone: Tone = 'success'
  if (needsReview || confidence < 0.6) tone = 'danger'
  else if (confidence < 0.8) tone = 'warning'

  return (
    <Badge tone={tone} title={needsReview ? 'Flagged for manual review' : `${pct}% confidence`}>
      {needsReview ? <AlertTriangle className="h-3 w-3" aria-hidden="true" /> : null}
      <span className="tabular-nums">{pct}%</span>
    </Badge>
  )
}
