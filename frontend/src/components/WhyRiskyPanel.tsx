import { useState, useCallback } from 'react'
import { ShieldAlert, ChevronDown, ChevronUp, RefreshCw, AlertTriangle } from 'lucide-react'
import type { BidderRisk } from '../api/risk'
import { getBidderRisk, analyzeBidderRisk } from '../api/risk'
import { riskBadgeClass, riskBg, riskColor, severityBadgeClass } from '../lib/risk'
import RiskScoreCard from './RiskScoreCard'
import { getErrorMessage } from '../lib/errors'

interface Props {
  bidderId: string
  canAnalyze: boolean
}

const BREAKDOWN_LABELS: Record<string, string> = {
  compliance_failures: 'Compliance Failures',
  government_mismatches: 'Government Registry Mismatches',
  suspicious_documents: 'Suspicious Documents',
  missing_documents: 'Missing Documents',
  identity_inconsistency: 'Identity Inconsistency',
  duplicate_documents: 'Duplicate Documents',
}

export default function WhyRiskyPanel({ bidderId, canAnalyze }: Props) {
  const [open, setOpen] = useState(false)
  const [risk, setRisk] = useState<BidderRisk | null>(null)
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getBidderRisk(bidderId)
      setRisk(data)
    } catch {
      setError('Risk analysis not yet run.')
    } finally {
      setLoading(false)
    }
  }, [bidderId])

  const handleOpen = () => {
    setOpen(true)
    if (!risk) load()
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setError(null)
    try {
      const data = await analyzeBidderRisk(bidderId)
      setRisk(data)
    } catch (err) {
      setError(getErrorMessage(err, 'Risk analysis failed.'))
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      {/* Trigger button */}
      <button
        onClick={open ? () => setOpen(false) : handleOpen}
        className="flex w-full items-center justify-between rounded-xl px-5 py-4 text-left transition-colors hover:bg-slate-50"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-100 text-orange-600">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold text-slate-800">Why Is This Bidder Risky?</p>
            <p className="text-xs text-slate-500">Risk Intelligence — deterministic analysis</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {risk && (
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${riskBadgeClass(risk.risk_level)}`}>
              {Math.round(risk.risk_score)}/100
            </span>
          )}
          {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-100 px-5 pb-5 pt-4">
          {loading && (
            <div className="py-6 text-center text-sm text-slate-400">Loading risk analysis…</div>
          )}

          {error && !risk && (
            <div className="space-y-3 py-4 text-center">
              <p className="text-sm text-slate-500">{error}</p>
              {canAnalyze && (
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60"
                >
                  <RefreshCw className={`h-4 w-4 ${analyzing ? 'animate-spin' : ''}`} />
                  {analyzing ? 'Analyzing…' : 'Run Risk Analysis'}
                </button>
              )}
            </div>
          )}

          {risk && (
            <div className="space-y-5">
              {/* Header row */}
              <div className="flex flex-wrap items-start gap-4">
                <RiskScoreCard score={risk.risk_score} level={risk.risk_level} compact />
                <div className="flex-1 space-y-2">
                  {canAnalyze && (
                    <button
                      onClick={handleAnalyze}
                      disabled={analyzing}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-60"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${analyzing ? 'animate-spin' : ''}`} />
                      {analyzing ? 'Re-analyzing…' : 'Re-run Analysis'}
                    </button>
                  )}
                  {risk.analyzed_at && (
                    <p className="text-xs text-slate-400">
                      Last analysed: {new Date(risk.analyzed_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>

              {/* AI Summary */}
              {risk.ai_summary && (
                <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-blue-700">
                    AI Risk Summary (advisory only — does not affect verdict)
                  </p>
                  <p className="text-sm text-blue-900">{risk.ai_summary}</p>
                </div>
              )}

              {/* Score breakdown */}
              {risk.breakdown && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Score Breakdown</p>
                  <div className="space-y-1.5">
                    {Object.entries(risk.breakdown).map(([key, val]) => {
                      if (!val) return null
                      const pct = Math.min(100, (val / risk.risk_score) * 100)
                      return (
                        <div key={key} className="flex items-center gap-3">
                          <p className="w-52 shrink-0 text-xs text-slate-600">{BREAKDOWN_LABELS[key] ?? key}</p>
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                            <div className="h-full rounded-full bg-orange-400" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="w-8 text-right text-xs font-semibold text-slate-700">+{Math.round(val)}</span>
                        </div>
                      )
                    })}
                  </div>
                  <p className="mt-1 text-right text-xs text-slate-500">Total: {Math.round(risk.risk_score)}/100</p>
                </div>
              )}

              {/* Risk factors */}
              {risk.factors.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Primary Risk Factors
                  </p>
                  <div className="space-y-2">
                    {risk.factors.map((f, i) => (
                      <div key={i} className={`flex items-start gap-3 rounded-lg border p-3 ${riskBg(f.severity)}`}>
                        <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${riskColor(f.severity)}`} />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-semibold text-slate-800">{f.factor}</p>
                            <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${severityBadgeClass(f.severity)}`}>
                              {f.severity.toUpperCase()}
                            </span>
                            <span className="ml-auto text-xs font-semibold text-slate-600">+{f.score_contribution}</span>
                          </div>
                          <p className="mt-0.5 text-xs text-slate-600">{f.detail}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
