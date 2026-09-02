import ScoreIndicator from './ui/ScoreIndicator'

/**
 * Horizontal compliance-score bar. Thin wrapper over the shared ScoreIndicator
 * (bar variant) so existing call sites keep working while the visual comes from
 * the design system (threshold-based colour + numeric label).
 */
export default function ComplianceScoreBar({ score }: { score: number }) {
  return <ScoreIndicator score={score} variant="bar" />
}
