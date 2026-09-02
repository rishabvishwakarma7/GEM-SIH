import { riskBadgeClass, riskBg, riskColor, riskLabel } from '../lib/risk'

interface Props {
  score: number | null
  level: string | null
  compact?: boolean
}

export default function RiskScoreCard({ score, level, compact = false }: Props) {
  if (score === null || score === undefined) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-center text-sm text-slate-400">
        Risk score unavailable — run risk analysis first
      </div>
    )
  }

  const radius = compact ? 28 : 40
  const stroke = compact ? 6 : 8
  const circumference = 2 * Math.PI * radius
  const progress = circumference - (score / 100) * circumference

  const colorClass = riskColor(level)
  const strokeColor =
    level === 'critical' ? '#b91c1c'
    : level === 'high' ? '#ea580c'
    : level === 'medium' ? '#ca8a04'
    : '#16a34a'

  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <svg width="72" height="72" className="shrink-0">
          <circle cx="36" cy="36" r={radius} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
          <circle
            cx="36" cy="36" r={radius} fill="none"
            stroke={strokeColor} strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={progress}
            strokeLinecap="round"
            transform="rotate(-90 36 36)"
          />
          <text x="36" y="40" textAnchor="middle" fontSize="14" fontWeight="700" fill={strokeColor}>
            {Math.round(score)}
          </text>
        </svg>
        <div>
          <p className="text-xs text-slate-500">Risk Score</p>
          <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${riskBadgeClass(level)}`}>
            {riskLabel(level)}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className={`rounded-xl border p-6 ${riskBg(level)}`}>
      <div className="flex flex-col items-center gap-4">
        <svg width="120" height="120">
          <circle cx="60" cy="60" r={radius} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
          <circle
            cx="60" cy="60" r={radius} fill="none"
            stroke={strokeColor} strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={progress}
            strokeLinecap="round"
            transform="rotate(-90 60 60)"
          />
          <text x="60" y="56" textAnchor="middle" fontSize="26" fontWeight="800" fill={strokeColor}>
            {Math.round(score)}
          </text>
          <text x="60" y="72" textAnchor="middle" fontSize="11" fill="#64748b">
            / 100
          </text>
        </svg>
        <div className="text-center">
          <p className="text-sm font-medium text-slate-600">Overall Risk Score</p>
          <span className={`mt-1 inline-block rounded-full px-3 py-1 text-sm font-bold ${riskBadgeClass(level)}`}>
            {riskLabel(level)} Risk
          </span>
        </div>
      </div>
    </div>
  )
}
