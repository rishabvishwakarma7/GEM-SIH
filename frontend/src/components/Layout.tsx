import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import Sidebar from './layout/Sidebar'
import Topbar from './layout/Topbar'

const COLLAPSE_KEY = 'sidebar_collapsed'

/**
 * Application shell: a persistent left sidebar (branding + role-aware
 * navigation + account) and a top utility bar (search, notifications, user
 * menu) wrapping the routed page content. Preserves the `<Layout>{children}`
 * contract used by every page.
 */
export default function Layout({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === '1'
    } catch {
      return false
    }
  })
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0')
    } catch {
      /* ignore persistence errors */
    }
  }, [collapsed])

  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        onToggleCollapse={() => setCollapsed((v) => !v)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenMobile={() => setMobileOpen(true)} />
        <main className="flex-1">
          <div className="mx-auto w-full max-w-7xl px-4 py-6 lg:px-8 lg:py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
