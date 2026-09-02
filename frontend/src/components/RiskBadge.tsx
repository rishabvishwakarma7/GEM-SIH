import { ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react'
import type { RiskLevel } from '../types'
import StatusBadge from './ui/StatusBadge'
import type { Tone } from './ui/Badge'

const TONE: Record<RiskLevel, Tone> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
}

const LABELS: Record<RiskLevel, string> = {
  low: 'Low Risk',
  medium: 'Medium Risk',
  high: 'High Risk',
}

const ICON: Record<RiskLevel, JSX.Element> = {
  low: <ShieldCheck className="h-3.5 w-3.5" />,
  medium: <ShieldAlert className="h-3.5 w-3.5" />,
  high: <ShieldX className="h-3.5 w-3.5" />,
}

export default function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <StatusBadge tone={TONE[level]} icon={ICON[level]}>
      {LABELS[level]}
    </StatusBadge>
  )
}
