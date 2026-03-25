import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  FolderGit2, Search, Activity, ArrowRight, GitBranch, FileCode,
  AlertTriangle, Zap, TrendingUp, Clock, Shield, CheckCircle2,
  ArrowUpRight, Bug, Code2, BarChart3, Loader2
} from 'lucide-react'

import { repositoryAPI, activityAPI } from '../services/api'

const typeConfig = {
  ERROR:        { bg: 'rgba(239,68,68,0.1)',  color: '#ef4444', icon: Bug },
  OPTIMIZATION: { bg: 'rgba(59,130,246,0.1)',  color: '#3b82f6', icon: TrendingUp },
  REFACTOR:     { bg: 'rgba(168,85,247,0.1)',  color: '#a855f7', icon: Code2 },
  FEATURE:      { bg: 'rgba(16,185,129,0.1)',  color: '#10b981', icon: CheckCircle2 },
}

const healthMetrics = [
  { label: 'Code Quality', value: 87, color: '#10b981' },
  { label: 'Test Coverage', value: 72, color: '#3b82f6' },
  { label: 'Security Score', value: 95, color: '#8b5cf6' },
  { label: 'Performance', value: 91, color: '#f59e0b' },
]

export default function Dashboard() {
  const [repos, setRepos] = useState([])
  const [activities, setActivities] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [repoRes, activityRes] = await Promise.all([
          repositoryAPI.list(),
          activityAPI.getAll({ limit: 5 })
        ])
        setRepos(repoRes.data.repositories || [])
        setActivities(activityRes.data.activities || [])
      } catch (err) {
        console.error('Dashboard fetch error:', err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [])

  const stats = [
    { label: 'Repositories', value: repos.length.toString(), change: '+1 this week', icon: FolderGit2, color: '#8b5cf6' },
    { label: 'Files Indexed', value: repos.reduce((acc, r) => acc + (r.indexed_files || 0), 0).toLocaleString(), change: 'Real-time', icon: FileCode, color: '#10b981' },
    { label: 'Issues Found', value: activities.length.toString(), change: 'AI Detected', icon: AlertTriangle, color: '#f59e0b' },
    { label: 'AI Fixes Ready', value: activities.filter(a => !!a.code_patch).length.toString(), change: 'Click to view', icon: Zap, color: '#3b82f6' },
  ]

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <Loader2 className="animate-spin" style={{ color: 'var(--color-accent)', width: '40px', height: '40px' }} />
      </div>
    )
  }

  return (
    <div style={{ padding: '32px', height: '100%', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
      {/* ── Header ── */}
      <div style={{ marginBottom: '28px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.02em' }}>
            Dashboard
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
            Overview of your repositories and recent debugging activity.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <Link
            to="/repositories"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              padding: '9px 18px', borderRadius: '10px', fontSize: '13px', fontWeight: 600,
              background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
              color: 'var(--color-text-secondary)', textDecoration: 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <GitBranch style={{ width: '15px', height: '15px' }} /> Connect Repo
          </Link>
          <Link
            to="/debug"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              padding: '9px 18px', borderRadius: '10px', fontSize: '13px', fontWeight: 600,
              background: 'var(--color-accent)', color: 'white', textDecoration: 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <Search style={{ width: '15px', height: '15px' }} /> Debug Assistant
          </Link>
        </div>
      </div>

      {/* ── Stats Grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        {stats.map((s) => (
          <div
            key={s.label}
            style={{
              background: 'var(--color-bg-card)',
              border: '1px solid var(--color-border)',
              borderRadius: '14px',
              padding: '24px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
              background: `linear-gradient(90deg, ${s.color}, transparent)`,
              opacity: 0.6,
            }} />
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{
                width: '42px', height: '42px', borderRadius: '12px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: `${s.color}15`,
              }}>
                <s.icon style={{ width: '20px', height: '20px', color: s.color }} strokeWidth={1.5} />
              </div>
              <ArrowUpRight style={{ width: '16px', height: '16px', color: 'var(--color-text-muted)', opacity: 0.5 }} />
            </div>
            <p style={{ fontSize: '32px', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.02em', lineHeight: 1 }}>
              {s.value}
            </p>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px' }}>
              <p style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>{s.label}</p>
              <p style={{ fontSize: '11px', color: s.color, fontWeight: 500 }}>{s.change}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Main Content Area ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px', flex: 1, minHeight: 0 }}>
        {/* Left: Recent Activity */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-primary)' }}>Recent Activity</h2>
            <Link to="/activity" style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-accent)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
              View all <ArrowRight style={{ width: '14px', height: '14px' }} />
            </Link>
          </div>
          <div style={{
            flex: 1, background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
            borderRadius: '14px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', overflow: 'hidden',
            display: 'flex', flexDirection: 'column',
          }}>
            {activities.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                No recent activity.
              </div>
            ) : activities.map((item, i) => {
              const cfg = typeConfig[item.category] || typeConfig.ERROR
              const TypeIcon = cfg.icon
              return (
                <div key={i} style={{
                  display: 'flex', alignItems: 'flex-start', gap: '14px', padding: '18px 22px',
                  borderBottom: i < activities.length - 1 ? '1px solid var(--color-border)' : 'none',
                }}>
                  <div style={{
                    width: '34px', height: '34px', borderRadius: '10px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: cfg.bg, flexShrink: 0, marginTop: '2px',
                  }}>
                    <TypeIcon style={{ width: '16px', height: '16px', color: cfg.color }} strokeWidth={2} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '3px' }}>
                      <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.error}
                      </p>
                      <span style={{
                        fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', padding: '2px 8px', borderRadius: '6px',
                        background: cfg.bg, color: cfg.color,
                      }}>
                        {item.category}
                      </span>
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>{item.root_cause}</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', background: 'var(--color-bg-elevated)', padding: '1px 8px', borderRadius: '4px' }}>
                        {item.file_path}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock style={{ width: '11px', height: '11px' }} /> {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Right: Health Metrics + Quick Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '14px', padding: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
               <BarChart3 style={{ width: '16px', height: '16px', color: '#8b5cf6' }} />
               <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-primary)' }}>System Health</h3>
            </div>
            {healthMetrics.map((m) => (
              <div key={m.label} style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>{m.label}</span>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: m.color }}>{m.value}%</span>
                </div>
                <div style={{ height: '6px', borderRadius: '3px', background: 'var(--color-bg-elevated)', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${m.value}%`, background: m.color }} />
                </div>
              </div>
            ))}
          </div>

          <div style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '14px', padding: '22px', flex: 1 }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '16px' }}>Quick Actions</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[
                { to: '/debug', label: 'Debug Assistant', icon: Search, color: '#8b5cf6' },
                { to: '/repositories', label: 'Connect Repository', icon: GitBranch, color: '#10b981' },
                { to: '/activity', label: 'View Activity', icon: Activity, color: '#3b82f6' },
                { to: '/analysis', label: 'Root Cause Analysis', icon: Shield, color: '#f59e0b' },
              ].map((a) => (
                <Link key={a.to} to={a.to} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', borderRadius: '10px', textDecoration: 'none', background: 'var(--color-bg-elevated)' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${a.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <a.icon style={{ width: '16px', height: '16px', color: a.color }} />
                  </div>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{a.label}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
