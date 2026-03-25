import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, FolderGit2, Bug, Search, Activity, Settings } from 'lucide-react'

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/' },
  { label: 'Repositories', icon: FolderGit2, path: '/repositories' },
  { label: 'Debug Assistant', icon: Bug, path: '/debug' },
  { label: 'Analysis', icon: Search, path: '/analysis' },
  { label: 'Activity', icon: Activity, path: '/activity' },
  { label: 'Settings', icon: Settings, path: '/settings' },
]

export default function Layout({ children }) {
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-bg-primary)' }}>
      {/* ──── Sidebar ──── */}
      <aside
        className="w-[260px] h-screen flex flex-col shrink-0"
        style={{
          background: 'var(--color-bg-sidebar)',
          borderRight: '1px solid var(--color-border)',
        }}
      >
        {/* ── Brand ── */}
        <div className="flex items-center gap-3 px-4" style={{ height: '72px' }}>
          <div
            className="flex items-center justify-center shrink-0"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
              <path d="M8 2L14 6V10L8 14L2 10V6L8 2Z" fill="white" fillOpacity="0.9" />
            </svg>
          </div>
          <span className="font-semibold tracking-tight" style={{ fontSize: '18px', color: 'var(--color-text-primary)' }}>
            CodeSage AI
          </span>
        </div>

        {/* ── Navigation ── */}
        <nav className="flex-1 px-3 mt-2">
          <div className="space-y-1">
            {navItems.map((item) => {
              const isActive =
                location.pathname === item.path ||
                (item.path !== '/' && location.pathname.startsWith(item.path))

              return (
                <Link
                  key={item.label}
                  to={item.path}
                  className="sidebar-item flex items-center gap-3"
                  style={{
                    height: '44px',
                    padding: '10px 14px',
                    borderRadius: '10px',
                    fontSize: '14px',
                    fontWeight: 500,
                    color: isActive ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                    background: isActive ? 'var(--color-accent-subtle)' : 'transparent',
                    border: isActive ? '1px solid var(--color-accent-muted)' : '1px solid transparent',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <item.icon style={{ width: '18px', height: '18px' }} strokeWidth={isActive ? 2 : 1.5} />
                  {item.label}
                </Link>
              )
            })}
          </div>
        </nav>

        {/* ── Profile ── */}
        <div className="px-3 pb-4">
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px', marginBottom: '4px' }} />
          <div
            className="flex items-center gap-3"
            style={{
              background: 'rgba(255,255,255,0.02)',
              padding: '10px',
              borderRadius: '10px',
            }}
          >
            <div
              className="flex items-center justify-center text-[11px] font-bold text-white shrink-0"
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #8b5cf6, #a855f7)',
              }}
            >
              YM
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>Yash Mishra</p>
              <p className="text-[11px] truncate" style={{ color: 'var(--color-text-muted)' }}>yash@codesage.ai</p>
            </div>
          </div>
        </div>
      </aside>

      {/* ──── Main Content ──── */}
      <main className="flex-1 overflow-hidden" style={{ height: '100vh' }}>
        {children}
      </main>
    </div>
  )
}
