import { useEffect, useState } from 'react'
import { ShieldCheck, Play, RotateCw, CheckCircle2, Loader2, Sparkles, BellRing, Send } from 'lucide-react'
import type { ComplianceResultDetail, Notification } from '../types'
import { runVerification } from '../api/verification'
import { evaluateBidderCompliance, getBidderCompliance } from '../api/compliance'
import { listBidderNotifications, sendBidderAlert } from '../api/notifications'
import { getErrorMessage } from '../lib/errors'
import ComplianceStatusBadge from './ComplianceStatusBadge'
import RiskBadge from './RiskBadge'
import RequirementResultsTable from './RequirementResultsTable'
import { SectionCard } from './ui/Card'
import Button from './ui/Button'
import Alert from './ui/Alert'
import Badge from './ui/Badge'
import ScoreIndicator from './ui/ScoreIndicator'
import EmptyState from './ui/EmptyState'
import { SkeletonText } from './ui/Skeleton'
import { cn } from '../lib/cn'
import { formatRelativeTime } from '../lib/format'

const PROGRESS_STEPS = [
  'Matching tender requirements to bidder documents',
  'Querying simulated government registries (GST / PAN / Udyam / MCA / BIS / Blacklist)',
  'Running the deterministic compliance rule engine',
  'Finalising compliance score and risk level',
]

interface Props {
  bidderId: string
  canManage: boolean
}

/**
 * AI-assisted compliance verification for a single bidder. Runs the mock
 * verification providers, then the deterministic rule engine, and renders the
 * resulting score, status, risk and per-requirement breakdown.
 */
export default function ComplianceDashboardPanel({ bidderId, canManage }: Props) {
  const [result, setResult] = useState<ComplianceResultDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRunning, setIsRunning] = useState(false)
  const [progressStep, setProgressStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const [notifications, setNotifications] = useState<Notification[]>([])
  const [isSendingAlert, setIsSendingAlert] = useState(false)
  const [alertError, setAlertError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setIsLoading(true)
    getBidderCompliance(bidderId)
      .then((data) => {
        if (mounted) setResult(data)
      })
      .catch(() => mounted && setError('Failed to load compliance result'))
      .finally(() => mounted && setIsLoading(false))
    listBidderNotifications(bidderId)
      .then((data) => mounted && setNotifications(data))
      .catch(() => {
        /* non-critical - notification history is a nice-to-have here */
      })
    return () => {
      mounted = false
    }
  }, [bidderId])

  async function handleSendAlert() {
    setAlertError(null)
    setIsSendingAlert(true)
    try {
      const sent = await sendBidderAlert(bidderId)
      setNotifications((prev) => [sent, ...prev])
    } catch (err) {
      setAlertError(getErrorMessage(err, 'Could not send alert.'))
    } finally {
      setIsSendingAlert(false)
    }
  }

  async function handleRunVerificationAndEvaluate() {
    setError(null)
    setIsRunning(true)
    setProgressStep(0)
    try {
      // Staged progress purely for UX — the mock providers respond fast, so
      // without this the button would just flash a spinner for a fraction of a
      // second. Each step below corresponds to a real phase of work.
      setProgressStep(1)
      await runVerification(bidderId)
      setProgressStep(2)
      await new Promise((r) => setTimeout(r, 350))
      setProgressStep(3)
      const evaluated = await evaluateBidderCompliance(bidderId)
      setProgressStep(4)
      await new Promise((r) => setTimeout(r, 250))
      setResult(evaluated)
      listBidderNotifications(bidderId).then(setNotifications).catch(() => {})
    } catch (err) {
      setError(getErrorMessage(err, 'Verification / evaluation failed. Please try again.'))
    } finally {
      setIsRunning(false)
      setProgressStep(0)
    }
  }

  return (
    <SectionCard
      icon={<ShieldCheck className="h-4 w-4" />}
      title="Compliance verification"
      description="Simulated government registry checks, then a deterministic rule engine."
      flush
      actions={
        canManage ? (
          <Button
            size="sm"
            variant={result ? 'outline' : 'primary'}
            onClick={handleRunVerificationAndEvaluate}
            loading={isRunning}
            leftIcon={result ? <RotateCw className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          >
            {isRunning ? 'Running…' : result ? 'Re-run verification' : 'Run verification'}
          </Button>
        ) : null
      }
    >
      {isRunning && (
        <div className="border-b border-slate-100 bg-primary-50/60 px-5 py-4">
          <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-primary-100">
            <div
              className="h-full rounded-full bg-primary-500 transition-all duration-300"
              style={{ width: `${(progressStep / PROGRESS_STEPS.length) * 100}%` }}
            />
          </div>
          <ul className="space-y-1.5 text-xs">
            {PROGRESS_STEPS.map((step, idx) => {
              const done = idx < progressStep
              const active = idx === progressStep - 1
              return (
                <li
                  key={step}
                  className={cn(
                    'flex items-center gap-2',
                    done ? 'font-medium text-primary-800' : 'text-primary-400',
                  )}
                >
                  {done && !active ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success-600" />
                  ) : active ? (
                    <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary-600" />
                  ) : (
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-300" />
                  )}
                  {step}
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {error && (
        <div className="px-5 pt-5">
          <Alert variant="danger" onDismiss={() => setError(null)}>
            {error}
          </Alert>
        </div>
      )}

      {isLoading ? (
        <div className="px-5 py-6">
          <SkeletonText lines={4} />
        </div>
      ) : !result ? (
        <EmptyState
          icon={<ShieldCheck className="h-6 w-6" />}
          title="Not yet evaluated"
          description={
            canManage
              ? 'Run verification to check this bidder against the tender requirements.'
              : 'This bidder has not been evaluated for compliance yet.'
          }
          action={
            canManage ? (
              <Button
                onClick={handleRunVerificationAndEvaluate}
                loading={isRunning}
                leftIcon={<Play className="h-4 w-4" />}
              >
                Run verification
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div>
          {/* Summary */}
          <div className="grid grid-cols-1 gap-5 border-b border-slate-100 px-5 py-6 sm:grid-cols-3">
            <div className="flex items-center gap-4">
              <ScoreIndicator score={result.compliance_score} size={72} />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Compliance score
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {result.compliant_count} of {result.total_requirements} requirements met
                </p>
              </div>
            </div>
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Final status
              </p>
              <ComplianceStatusBadge status={result.overall_status} />
              {result.mandatory_failed && (
                <p className="mt-2 text-xs font-medium text-danger-600">
                  A mandatory requirement failed — this overrides the numeric score.
                </p>
              )}
            </div>
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Risk indicator
              </p>
              <RiskBadge level={result.risk_level} />
            </div>
          </div>

          {result.explanation && (
            <div className="border-b border-slate-100 px-5 py-4 text-sm leading-relaxed text-slate-600">
              {result.explanation}
            </div>
          )}

          {result.ai_recommendation && (
            <div className="border-b border-slate-100 bg-primary-50/50 px-5 py-4">
              <p className="mb-1.5 inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-primary-700">
                <Sparkles className="h-3.5 w-3.5" />
                AI recommendation
              </p>
              <p className="text-sm leading-relaxed text-slate-700">{result.ai_recommendation}</p>
            </div>
          )}

          {/* Count chips */}
          <div className="flex flex-wrap gap-4 border-b border-slate-100 px-5 py-3 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-success-500" />
              <span className="font-semibold tabular-nums text-slate-700">
                {result.compliant_count}
              </span>{' '}
              Compliant
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-danger-500" />
              <span className="font-semibold tabular-nums text-slate-700">
                {result.non_compliant_count}
              </span>{' '}
              Non-Compliant
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-warning-500" />
              <span className="font-semibold tabular-nums text-slate-700">
                {result.needs_review_count}
              </span>{' '}
              Needs Review
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-slate-400" />
              <span className="font-semibold tabular-nums text-slate-700">
                {result.total_requirements}
              </span>{' '}
              Total
            </span>
          </div>

          <RequirementResultsTable results={result.requirement_results} />

          {/* Notifications / alerts (Day 6) */}
          {(result.overall_status !== 'compliant' || notifications.length > 0) && (
            <div className="border-t border-slate-100 px-5 py-4">
              <div className="mb-2 flex items-center justify-between">
                <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <BellRing className="h-3.5 w-3.5" />
                  Bidder alerts
                </p>
                {canManage && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleSendAlert}
                    loading={isSendingAlert}
                    leftIcon={<Send className="h-3.5 w-3.5" />}
                  >
                    {isSendingAlert ? 'Sending…' : 'Send alert to bidder'}
                  </Button>
                )}
              </div>
              {alertError && (
                <Alert variant="danger" className="mb-2" onDismiss={() => setAlertError(null)}>
                  {alertError}
                </Alert>
              )}
              {notifications.length === 0 ? (
                <p className="text-xs text-slate-400">No alerts sent yet for this bidder.</p>
              ) : (
                <ul className="space-y-1.5">
                  {notifications.slice(0, 5).map((n) => (
                    <li key={n.id} className="flex items-center justify-between gap-3 text-xs text-slate-600">
                      <span className="truncate">
                        {n.channel.toUpperCase()} · {n.recipient || 'no recipient on file'}
                        {n.reason ? ` — ${n.reason}` : ''}
                      </span>
                      <span className="flex shrink-0 items-center gap-2">
                        <Badge
                          size="sm"
                          tone={n.status === 'sent' ? 'success' : n.status === 'failed' ? 'danger' : 'neutral'}
                        >
                          {n.status}
                        </Badge>
                        <span className="text-slate-400">{formatRelativeTime(n.created_at)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* AI-assisted disclaimer */}
          <div className="flex items-start gap-2 border-t border-slate-100 bg-slate-50/60 px-5 py-3 text-xs text-slate-500">
            <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary-500" aria-hidden="true" />
            <span>
              AI-assisted result. Registry checks are simulated for this prototype and extraction
              may contain errors — review flagged items against source documents before making an
              award decision.
            </span>
          </div>
        </div>
      )}
    </SectionCard>
  )
}
