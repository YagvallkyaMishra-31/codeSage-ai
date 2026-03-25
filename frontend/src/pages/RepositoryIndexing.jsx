import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Link as LinkIcon, MoreVertical, Clock, FolderGit2, Upload,
  Globe, ArrowUpRight, RefreshCw, Trash2, GitBranch, HardDrive,
  CheckCircle2, Loader2, AlertCircle, FileCode, Eye
} from 'lucide-react'

import { repositoryAPI } from '../services/api'

const statusConfig = {
  completed: { label: 'Healthy', color: '#10b981', bg: 'rgba(16,185,129,0.1)', icon: CheckCircle2 },
  scanning:  { label: 'Scanning', color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', icon: Loader2 },
  indexing:  { label: 'Indexing', color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', icon: Loader2 },
  cloning:   { label: 'Cloning', color: '#3b82f6', bg: 'rgba(59,130,246,0.1)', icon: Loader2 },
  failed:    { label: 'Error', color: '#ef4444', bg: 'rgba(239,68,68,0.1)', icon: AlertCircle },
}

const langColors = {
  JavaScript: '#f59e0b', TypeScript: '#3b82f6', Python: '#10b981', Go: '#06b6d4',
  Rust: '#f97316', Java: '#ef4444', 'C++': '#a855f7', C: '#64748b', 'C#': '#16a34a',
  Ruby: '#ef4444', PHP: '#6366f1', Swift: '#f97316', Kotlin: '#a855f7', Vue: '#10b981',
  Svelte: '#f97316', Scala: '#ef4444',
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export default function RepositoryIndexing() {
  const [activeTab, setActiveTab] = useState('url')
  const [repoUrl, setRepoUrl] = useState('')
  const [repositories, setRepositories] = useState([])
  const [activeIndexing, setActiveIndexing] = useState(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  // Fetch repositories
  const fetchRepos = useCallback(async () => {
    try {
      const res = await repositoryAPI.list()
      const data = res.data
      setRepositories(data.repositories || [])

      // Find active indexing repo
      const active = (data.repositories || []).find(
        r => r.status === 'scanning' || r.status === 'indexing' || r.status === 'cloning'
      )
      if (active) {
        const statusRes = await repositoryAPI.getStatus(active.id)
        setActiveIndexing(statusRes.data)
      } else {
        setActiveIndexing(null)
      }
    } catch (err) {
      console.error('Failed to fetch repos:', err)
    }
  }, [])

  useEffect(() => {
    fetchRepos()
  }, [fetchRepos])

  // Poll for active indexing progress
  useEffect(() => {
    if (!activeIndexing || activeIndexing.status === 'completed' || activeIndexing.status === 'failed') return
    const interval = setInterval(async () => {
      try {
        const res = await repositoryAPI.getStatus(activeIndexing.id)
        const data = res.data
        setActiveIndexing(data)
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval)
          fetchRepos() // Refresh repo list
        }
      } catch (err) {
        console.error('Poll error:', err)
      }
    }, 1500)
    return () => clearInterval(interval)
  }, [activeIndexing, fetchRepos])

  // Connect repository
  const handleConnect = async () => {
    if (!repoUrl.trim()) return
    setIsConnecting(true)
    setError('')
    try {
      const res = await repositoryAPI.connect({ repo_url: repoUrl.trim() })
      setRepoUrl('')
      setActiveIndexing(res.data.repository)
      fetchRepos()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setIsConnecting(false)
    }
  }

  return (
    <div style={{ padding: '32px', height: '100%', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
      {/* ── Header ── */}
      <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.02em' }}>
            Repositories
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
            Connect, index, and manage your codebases for AI-powered analysis.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
            {repositories.length} repositories connected
          </span>
        </div>
      </div>

      {/* ── Top Section: Connect + Active Indexing ── */}
      <div style={{ display: 'grid', gridTemplateColumns: activeIndexing ? '1fr 380px' : '1fr', gap: '20px', marginBottom: '24px' }}>
        {/* Connect Card */}
        <div style={{
          background: 'var(--color-bg-card)',
          border: '1px solid var(--color-border)',
          borderRadius: '14px',
          padding: '24px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '10px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'var(--color-accent-subtle)',
            }}>
              <FolderGit2 style={{ width: '18px', height: '18px', color: 'var(--color-accent)' }} strokeWidth={1.5} />
            </div>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-primary)' }}>Connect Repository</h3>
              <p style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>Add a new codebase for analysis</p>
            </div>
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: '4px', marginBottom: '18px', background: 'var(--color-bg-elevated)', padding: '4px', borderRadius: '10px' }}>
            {[
              { id: 'url', label: 'Repository URL', icon: Globe },
              { id: 'zip', label: 'Upload ZIP', icon: Upload },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                  padding: '10px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: 500,
                  border: 'none', cursor: 'pointer', transition: 'all 0.15s ease',
                  background: activeTab === tab.id ? 'var(--color-accent)' : 'transparent',
                  color: activeTab === tab.id ? 'white' : 'var(--color-text-secondary)',
                }}
              >
                <tab.icon style={{ width: '15px', height: '15px' }} strokeWidth={1.5} />
                {tab.label}
              </button>
            ))}
          </div>

          {/* URL Input */}
          {activeTab === 'url' ? (
            <>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '12px',
                padding: '14px 16px', borderRadius: '10px',
                background: 'var(--color-bg-input)', border: '1px solid var(--color-border)',
                transition: 'border-color 0.15s ease',
              }}>
                <LinkIcon style={{ width: '16px', height: '16px', color: 'var(--color-text-muted)', flexShrink: 0 }} strokeWidth={1.5} />
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
                  placeholder="https://github.com/organization/repository"
                  style={{
                    background: 'transparent', border: 'none', outline: 'none', flex: 1,
                    fontSize: '14px', color: 'var(--color-text-primary)',
                    fontFamily: 'var(--font-mono)',
                  }}
                />
                <button
                  onClick={handleConnect}
                  disabled={isConnecting || !repoUrl.trim()}
                  style={{
                    padding: '8px 20px', borderRadius: '8px', fontSize: '13px', fontWeight: 600,
                    background: isConnecting ? 'var(--color-text-muted)' : 'var(--color-accent)',
                    color: 'white', border: 'none', cursor: isConnecting ? 'wait' : 'pointer',
                    transition: 'all 0.15s ease', whiteSpace: 'nowrap',
                    opacity: !repoUrl.trim() ? 0.5 : 1,
                  }}
                >
                  {isConnecting ? 'Cloning...' : 'Index Repository'}
                </button>
              </div>
              {error && (
                <p style={{ fontSize: '12px', color: '#ef4444', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertCircle style={{ width: '14px', height: '14px' }} /> {error}
                </p>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '14px' }}>
                <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>Supported platforms:</span>
                {['GitHub', 'GitLab', 'Bitbucket', 'Azure DevOps'].map((p) => (
                  <span key={p} style={{
                    fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)',
                    padding: '3px 10px', borderRadius: '6px',
                    background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
                  }}>
                    {p}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div style={{
              border: '2px dashed var(--color-border)', borderRadius: '12px',
              padding: '40px', textAlign: 'center',
              background: 'var(--color-bg-elevated)',
            }}>
              <Upload style={{ width: '32px', height: '32px', color: 'var(--color-text-muted)', margin: '0 auto 12px' }} strokeWidth={1.5} />
              <p style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                Drag & drop your ZIP file here
              </p>
              <p style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>or click to browse (max 500 MB)</p>
            </div>
          )}
        </div>

        {/* Active Indexing Card — only shows when a repo is being indexed */}
        {activeIndexing && activeIndexing.status !== 'completed' && activeIndexing.status !== 'failed' && (
          <div style={{
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-border)',
            borderRadius: '14px',
            padding: '24px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
            position: 'relative',
            overflow: 'hidden',
          }}>
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
              background: 'linear-gradient(90deg, #f59e0b, #8b5cf6, #3b82f6)',
            }} />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '8px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'rgba(245,158,11,0.1)',
                }}>
                  <Loader2 style={{ width: '16px', height: '16px', color: '#f59e0b', animation: 'spin 1s linear infinite' }} strokeWidth={2} />
                </div>
                <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-primary)' }}>Active Indexing</h3>
              </div>
              <span style={{
                fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em',
                padding: '4px 10px', borderRadius: '6px',
                background: 'rgba(245,158,11,0.1)', color: '#f59e0b',
              }}>
                {activeIndexing.status === 'cloning' ? 'Cloning' : 'In Progress'}
              </span>
            </div>

            <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '2px' }}>
              {activeIndexing.name}
            </p>
            <p style={{ fontSize: '12px', color: 'var(--color-accent)', marginBottom: '18px', fontFamily: 'var(--font-mono)' }}>
              {activeIndexing.url}
            </p>

            {/* Progress */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>Overall Progress</span>
              <span style={{ fontSize: '14px', fontWeight: 700, color: '#f59e0b' }}>
                {activeIndexing.progress_percent || 0}%
              </span>
            </div>
            <div style={{ height: '8px', borderRadius: '4px', background: 'var(--color-bg-elevated)', overflow: 'hidden', marginBottom: '20px' }}>
              <div style={{
                height: '100%', width: `${activeIndexing.progress_percent || 0}%`, borderRadius: '4px',
                background: 'linear-gradient(90deg, #f59e0b, #f97316)',
                transition: 'width 0.5s ease',
              }} />
            </div>

            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '18px' }}>
              {[
                { label: 'Files Scanned', value: activeIndexing.total_files?.toLocaleString() || '0' },
                { label: 'Indexed', value: activeIndexing.indexed_files?.toLocaleString() || '0' },
              ].map((s) => (
                <div key={s.label} style={{
                  padding: '14px', borderRadius: '10px', textAlign: 'center',
                  background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
                }}>
                  <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: '6px' }}>
                    {s.label}
                  </p>
                  <p style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-text-primary)', lineHeight: 1 }}>{s.value}</p>
                </div>
              ))}
            </div>

            {/* Languages */}
            {activeIndexing.languages && activeIndexing.languages !== '[]' && (
              <div style={{ marginBottom: '16px' }}>
                <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: '8px' }}>
                  Languages Detected
                </p>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {JSON.parse(activeIndexing.languages).map((l) => (
                    <span key={l} style={{
                      fontSize: '11px', fontWeight: 600, padding: '3px 10px', borderRadius: '6px',
                      background: `${langColors[l] || '#64748b'}18`, color: langColors[l] || '#64748b',
                      fontFamily: 'var(--font-mono)',
                    }}>
                      {l}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Repository Cards Grid ── */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            Your Repositories
          </h2>
          <button
            onClick={fetchRepos}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '7px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 500,
              background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
              color: 'var(--color-text-secondary)', cursor: 'pointer', transition: 'all 0.15s ease',
            }}
          >
            <RefreshCw style={{ width: '13px', height: '13px' }} strokeWidth={1.5} /> Refresh All
          </button>
        </div>

        {repositories.length === 0 ? (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: '1px dashed var(--color-border)', borderRadius: '14px',
            background: 'var(--color-bg-card)',
          }}>
            <div style={{ textAlign: 'center' }}>
              <FolderGit2 style={{ width: '48px', height: '48px', color: 'var(--color-text-muted)', margin: '0 auto 16px' }} strokeWidth={1} />
              <p style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                No repositories connected
              </p>
              <p style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
                Paste a GitHub URL above to get started
              </p>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', flex: 1 }}>
            {repositories.map((p) => {
              const sc = statusConfig[p.status] || statusConfig.completed
              const StatusIcon = sc.icon
              const langs = p.languages ? JSON.parse(p.languages) : []
              const progress = p.total_files ? Math.round((p.indexed_files / p.total_files) * 100) : 0
              return (
                <div
                  key={p.id}
                  className="card-hover"
                  style={{
                    background: 'var(--color-bg-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '14px',
                    padding: '22px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    flexDirection: 'column',
                  }}
                >
                  {/* Header */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{
                        width: '38px', height: '38px', borderRadius: '10px',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
                      }}>
                        <FolderGit2 style={{ width: '18px', height: '18px', color: 'var(--color-text-secondary)' }} strokeWidth={1.5} />
                      </div>
                      <div>
                        <p style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{p.name}</p>
                        <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{p.url}</p>
                      </div>
                    </div>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: '5px',
                      fontSize: '11px', fontWeight: 600, padding: '4px 10px', borderRadius: '6px',
                      background: sc.bg, color: sc.color,
                    }}>
                      <StatusIcon style={{ width: '12px', height: '12px' }} strokeWidth={2} />
                      {sc.label}
                    </span>
                  </div>

                  {/* Languages */}
                  {langs.length > 0 && (
                    <div style={{ display: 'flex', gap: '6px', marginBottom: '16px', flexWrap: 'wrap' }}>
                      {langs.map((lang) => (
                        <span key={lang} style={{
                          fontSize: '11px', fontWeight: 600, padding: '3px 10px', borderRadius: '6px',
                          background: `${langColors[lang] || '#64748b'}15`, color: langColors[lang] || '#64748b',
                          fontFamily: 'var(--font-mono)',
                        }}>
                          {lang}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Stats Row */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
                    {[
                      { label: 'Files', value: p.total_files?.toLocaleString() || '0', icon: FileCode },
                      { label: 'Size', value: formatBytes(p.repo_size_bytes), icon: HardDrive },
                      { label: 'Branches', value: p.branches || 1, icon: GitBranch },
                    ].map((s) => (
                      <div key={s.label} style={{
                        padding: '10px', borderRadius: '8px', textAlign: 'center',
                        background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
                      }}>
                        <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: '4px' }}>
                          {s.label}
                        </p>
                        <p style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary)', lineHeight: 1 }}>{s.value}</p>
                      </div>
                    ))}
                  </div>

                  {/* Coverage progress */}
                  <div style={{ marginTop: 'auto' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>Index Coverage</span>
                      <span style={{ fontSize: '12px', fontWeight: 600, color: progress >= 80 ? '#10b981' : progress >= 50 ? '#f59e0b' : '#ef4444' }}>
                        {progress}%
                      </span>
                    </div>
                    <div style={{ height: '4px', borderRadius: '2px', background: 'var(--color-bg-elevated)', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', borderRadius: '2px', width: `${progress}%`,
                        background: progress >= 80 ? '#10b981' : progress >= 50 ? '#f59e0b' : '#ef4444',
                        transition: 'width 0.5s ease',
                      }} />
                    </div>
                  </div>

                  {/* Footer */}
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    paddingTop: '14px', marginTop: '14px', borderTop: '1px solid var(--color-border)',
                  }}>
                    <span style={{ fontSize: '12px', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <Clock style={{ width: '12px', height: '12px' }} strokeWidth={1.5} />
                      {p.created_at ? new Date(p.created_at).toLocaleDateString() : 'N/A'}
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/repo/${p.id}`) }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '5px',
                        padding: '5px 12px', borderRadius: '6px', fontSize: '11px', fontWeight: 600,
                        background: 'var(--color-accent)', border: 'none',
                        color: 'white', cursor: 'pointer', transition: 'all 0.15s ease',
                      }}
                    >
                      <Eye style={{ width: '12px', height: '12px' }} strokeWidth={1.5} /> View
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
