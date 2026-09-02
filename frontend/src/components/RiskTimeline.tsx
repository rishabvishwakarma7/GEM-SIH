import { useEffect, useState, useCallback } from 'react'
import { Clock } from 'lucide-react'
import { getBidderRiskTimeline } from '../api/risk'
import type { RiskTimelineEvent } from '../api/risk'

interface Props { bidderId: string }

const ACTION_LABELS: Record<string, string> = {
  document_uploaded: 'Document uploaded',
  document_processed: 'AI extraction completed',
  verification_run: 'Government verification run',
  compliance_evaluated: 'Compliance evaluation run',
  risk_analyzed: 'Risk analysis computed',
  review_case_created: 'Review case created',
  review_case_assigned: 'Review case assigned',
  review_action: 'Review action taken',
  review_case_escalated: 'Case escalated',
  final_decision_submitted: 'Final decision submitted',
}

function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action.replace(/_/g, ' ')
}

function actionColor(action: string): string {
  if (action.includes('fail') || action.includes('non_compliant')) return 'bg-red-500'
  if (action.includes('escalat') || action.includes('suspicious')) return 'bg-orange-500'
  if (action.includes('final_decision')) return 'bg-green-600'
  if (action.includes('review')) return 'bg-purple-500'
  if (action.includes('compliance')) return 'bg-blue-500'
  return 'bg-slate-400'
}

export default function RiskTimeline({ bidderId }: Props) {
  const [events, setEvents] = useState<RiskTimelineEvent[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const data = await getBidderRiskTimeline(bidderId)
      setEvents(data.events)
    } catch {
      // empty timeline is fine
    } finally {
      setLoading(false)
    }
  }, [bidderId])

  useEffect(() => { load() }, [load])

  if (loading) return <div className="py-4 text-center text-sm text-slate-400">Loading timeline…</div>
  if (!events.length) return <div className="py-4 text-center text-sm text-slate-400">No timeline events recorded yet.</div>

  return (
    <div className="relative space-y-0">
      {/* Vertical line */}
      <div className="absolute left-4 top-0 h-full w-0.5 bg-slate-100" />
      {events.map((e, i) => (
        <div key={i} className="relative flex items-start gap-4 pb-4 pl-10">
          <div className={`absolute left-2.5 mt-1.5 h-3 w-3 rounded-full ${actionColor(e.action)} ring-2 ring-white`} />
          <div className="min-w-0 flex-1 rounded-lg border border-slate-100 bg-white p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-slate-800">{actionLabel(e.action)}</p>
              {e.timestamp && (
                <span className="flex items-center gap-1 whitespace-nowrap text-xs text-slate-400">
                  <Clock className="h-3 w-3" />
                  {new Date(e.timestamp).toLocaleTimeString()}
                </span>
              )}
            </div>
            {e.timestamp && (
              <p className="text-xs text-slate-400">{new Date(e.timestamp).toLocaleDateString()}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
