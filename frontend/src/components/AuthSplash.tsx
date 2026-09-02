import { ShieldCheck } from 'lucide-react'
import { Loader2 } from 'lucide-react'

/** Branded full-screen loading state shown while the session is resolving. */
export default function AuthSplash() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-100">
      <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-brand-gradient shadow-elevated">
        <ShieldCheck className="h-7 w-7 text-white" />
      </div>
      <p className="text-sm font-semibold text-slate-800">GeM Bid Compliance Platform</p>
      <div className="mt-4 flex items-center gap-2 text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-xs">Verifying your session…</span>
      </div>
    </div>
  )
}
