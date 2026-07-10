import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, FileCode, AlertTriangle, Shield, Zap, Bug, Lightbulb,
  ChevronDown, ChevronRight, Loader2, Brain, Filter, RefreshCw
} from 'lucide-react'
import { analysisAPI } from '../services/api'

const severityConfig = {
  critical: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', label: 'Critical', icon: '🔴' },
  high:     { color: '#f97316', bg: 'rgba(249,115,22,0.12)', label: 'High', icon: '🟠' },
  medium:   { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', label: 'Medium', icon: '🟡' },
  low:      { color: '#10b981', bg: 'rgba(16,185,129,0.12)', label: 'Low', icon: '🟢' },
}

const typeIcons = {
  bug: Bug,
  security: Shield,
  performance: Zap,
  code_smell: AlertTriangle,
  improvement: Lightbulb,
}

const riskIndicator = {
  critical: '🔴',
  high: '🟠',
  medium: '🟡',
  clean: '🟢',
}

export default function RepoDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [summary, setSummary] = useState(null)
  const [files, setFiles] = useState([])
  const [issues, setIssues] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [expandedIssue, setExpandedIssue] = useState(null)
  const [severityFilter, setSeverityFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [issuesLoading, setIssuesLoading] = useState(false)
  const [groupByCategory, setGroupByCategory] = useState(true)
  const [reanalyzing, setReanalyzing] = useState(false)
  const pollRef = useRef(null)

  // Load all data
  const loadData = useCallback(async () => {
    try {
      const [sumRes, filesRes, issuesRes] = await Promise.all([
        analysisAPI.getSummary(id),
        analysisAPI.getFiles(id),
        analysisAPI.getIssues(id, {}),
      ])
      setSummary(sumRes.data)
      setFiles(filesRes.data.files || [])
      setIssues(issuesRes.data.issues || [])
      return sumRes.data
    } catch (err) {
      console.error('Failed to load repo details:', err)
      return null
    }
  }, [id])

  // Handle re-analyze
  const handleReanalyze = async () => {
    try {
      setReanalyzing(true)
      await analysisAPI.reanalyze(id)
      // Start polling for progress
      const sumData = await loadData()
      if (sumData?.analysis_status === 'analyzing') {
        startPolling()
      }
    } catch (err) {
      console.error('Re-analyze failed:', err)
      alert(err.response?.data?.detail || 'Failed to start re-analysis')
      setReanalyzing(false)
    }
  }

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      const data = await loadData()
      if (data && data.analysis_status !== 'analyzing') {
        clearInterval(pollRef.current)
        pollRef.current = null
        setReanalyzing(false)
      }
    }, 3000)
  }, [loadData])

  // Fetch on mount
  useEffect(() => {
    const init = async () => {
      const data = await loadData()
      setLoading(false)
      if (data?.analysis_status === 'analyzing') {
        setReanalyzing(true)
        startPolling()
      }
    }
    init()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [id, loadData, startPolling])

  // Fetch issues when file or severity filter changes
  useEffect(() => {
    const loadIssues = async () => {
      setIssuesLoading(true)
      try {
        const params = {}
        if (selectedFile) params.file_path = selectedFile
        if (severityFilter) params.severity = severityFilter
        const res = await analysisAPI.getIssues(id, params)
        setIssues(res.data.issues || [])
      } catch (err) {
        console.error('Failed to load issues:', err)
      } finally {
        setIssuesLoading(false)
      }
    }
    loadIssues()
  }, [id, selectedFile, severityFilter])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <Loader2 style={{ width: '32px', height: '32px', color: 'var(--color-accent)', animation: 'spin 1s linear infinite' }} />
      </div>
    )
  }

  const isAnalyzing = summary?.analysis_status === 'analyzing'

  return (
    <div style={{ padding: '24px', height: '100%', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
      {/* ── Back + Header ── */}
      <div style={{ marginBottom: '16px' }}>
        <button
          onClick={() => navigate('/repositories')}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px', background: 'none',
            border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '13px',
            padding: 0, marginBottom: '12px',
          }}
        >
          <ArrowLeft style={{ width: '14px', height: '14px' }} /> Back to Repositories
        </button>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.02em' }}>
              {summary?.name || 'Repository'}
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--color-accent)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
              {summary?.url}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {isAnalyzing ? (
              <span style={{
                display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600,
                padding: '6px 14px', borderRadius: '8px', background: 'rgba(245,158,11,0.1)', color: '#f59e0b',
              }}>
                <Loader2 style={{ width: '14px', height: '14px', animation: 'spin 1s linear infinite' }} />
                AI Analyzing...
              </span>
            ) : (
              <button
                onClick={handleReanalyze}
                disabled={reanalyzing}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600,
                  padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--color-border)',
                  background: reanalyzing ? 'var(--color-bg-elevated)' : 'var(--color-accent)',
                  color: reanalyzing ? 'var(--color-text-muted)' : 'white',
                  cursor: reanalyzing ? 'not-allowed' : 'pointer', transition: 'all 0.15s',
                  boxShadow: reanalyzing ? 'none' : '0 2px 8px rgba(139,92,246,0.3)',
                }}
              >
                <RefreshCw style={{ width: '14px', height: '14px', animation: reanalyzing ? 'spin 1s linear infinite' : 'none' }} />
                {reanalyzing ? 'Analyzing...' : 'Re-analyze'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── AI Summary Banner ── */}
      {summary?.analysis_status === 'analyzed' && (
        <div style={{
          background: (summary?.severity_breakdown?.critical > 0 || summary?.severity_breakdown?.high > 0)
            ? 'linear-gradient(135deg, rgba(239,68,68,0.06), rgba(249,115,22,0.06))'
            : 'linear-gradient(135deg, rgba(16,185,129,0.06), rgba(59,130,246,0.06))',
          border: `1px solid ${(summary?.severity_breakdown?.critical > 0 || summary?.severity_breakdown?.high > 0) ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}`,
          borderRadius: '12px', padding: '16px 20px', marginBottom: '16px',
          display: 'flex', alignItems: 'center', gap: '14px',
        }}>
          <Brain style={{ width: '24px', height: '24px', color: '#8b5cf6', flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              🧠 {summary.summary_message || `AI analyzed your repository and found ${summary.total_issues || 0} items`}
            </p>
            {summary?.total_issues > 0 && (
              <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
                {Object.entries(summary.severity_breakdown || {}).map(([sev, count]) => {
                  if (!count) return null
                  const cfg = severityConfig[sev]
                  return (
                    <span key={sev} style={{ fontSize: '12px', fontWeight: 600, color: cfg?.color }}>
                      {cfg?.icon} {count} {cfg?.label}
                    </span>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Deep Insights Panel ── */}
      {summary?.top_insights && summary.top_insights.length > 0 && (
        <div style={{
          background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
          borderRadius: '12px', padding: '16px 20px', marginBottom: '20px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        }}>
          <h2 style={{ fontSize: '15px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: 'var(--color-text-primary)' }}>
            <Brain style={{ width: '18px', height: '18px', color: '#8b5cf6' }} /> Deep Insights
          </h2>
          <div style={{ display: 'grid', gap: '12px' }}>
            {summary.top_insights.map((insight, idx) => (
              <div key={idx} style={{ padding: '12px', background: 'var(--color-bg-elevated)', borderRadius: '8px', borderLeft: '3px solid #8b5cf6' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>{insight.title}</h3>
                <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>{insight.description}</p>
                <div style={{ marginTop: '8px', display: 'flex', gap: '12px', fontSize: '12px' }}>
                  <span style={{ color: '#ef4444' }}><strong>Impact:</strong> {insight.impact}</span>
                  <span style={{ color: '#f59e0b' }}><strong>Risk:</strong> {insight.why_it_matters}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Stat Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '12px', marginBottom: '20px' }}>
        {[
          { label: 'Code Health', value: `${summary?.health_score || 0}/100`, color: summary?.health_score > 80 ? '#10b981' : (summary?.health_score > 50 ? '#f59e0b' : '#ef4444') },
          { label: 'Total Issues', value: summary?.total_issues || 0, color: '#8b5cf6' },
          { label: 'Critical', value: summary?.severity_breakdown?.critical || 0, color: '#ef4444' },
          { label: 'High', value: summary?.severity_breakdown?.high || 0, color: '#f97316' },
          { label: 'Bugs', value: summary?.bug_count || summary?.type_breakdown?.bug || 0, color: '#f59e0b' },
          { label: 'Security', value: summary?.type_breakdown?.security || 0, color: '#ef4444' },
          { label: 'Improvements', value: summary?.improvement_count || summary?.type_breakdown?.improvement || 0, color: '#10b981' },
        ].map(s => (
          <div key={s.label} style={{
            background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
            borderRadius: '10px', padding: '14px', textAlign: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
          }}>
            <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: '6px' }}>
              {s.label}
            </p>
            <p style={{ fontSize: '24px', fontWeight: 700, color: s.color, lineHeight: 1 }}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* ── Main Layout: File Explorer + Issues ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '16px', flex: 1, minHeight: 0 }}>
        {/* ── Left: File Explorer ── */}
        <div style={{
          background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
          borderRadius: '12px', overflow: 'hidden', display: 'flex', flexDirection: 'column',
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        }}>
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              File Explorer
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              {files.length} files
            </span>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '6px' }}>
            {/* Show All option */}
            <button
              onClick={() => setSelectedFile(null)}
              style={{
                width: '100%', textAlign: 'left', padding: '8px 10px', borderRadius: '6px',
                border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                fontSize: '12px', fontWeight: selectedFile === null ? 600 : 400,
                background: selectedFile === null ? 'var(--color-accent-subtle)' : 'transparent',
                color: selectedFile === null ? 'var(--color-accent)' : 'var(--color-text-secondary)',
              }}
            >
              <FileCode style={{ width: '13px', height: '13px' }} strokeWidth={1.5} />
              All Files
            </button>
            {files.map((f) => (
              <button
                key={f.file_path}
                onClick={() => setSelectedFile(f.file_path)}
                style={{
                  width: '100%', textAlign: 'left', padding: '7px 10px', borderRadius: '6px',
                  border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                  fontSize: '12px', transition: 'background 0.1s',
                  background: selectedFile === f.file_path ? 'var(--color-accent-subtle)' : 'transparent',
                  color: selectedFile === f.file_path ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                }}
              >
                <span>{riskIndicator[f.risk_level] || '🟢'}</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                  {f.file_path}
                </span>
                {f.issue_count > 0 && (
                  <span style={{
                    fontSize: '10px', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', minWidth: '18px', textAlign: 'center',
                    background: f.critical_count > 0 ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
                    color: f.critical_count > 0 ? '#ef4444' : '#f59e0b',
                  }}>
                    {f.issue_count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* ── Right: Issues Panel ── */}
        <div style={{
          background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
          borderRadius: '12px', overflow: 'hidden', display: 'flex', flexDirection: 'column',
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        }}>
          {/* Header with filters */}
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                Issues {selectedFile ? `— ${selectedFile.split('/').pop()}` : ''}
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', background: 'var(--color-bg-elevated)', padding: '2px 8px', borderRadius: '4px' }}>
                {issues.length}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <button
                onClick={() => setGroupByCategory(!groupByCategory)}
                style={{
                  fontSize: '11px', fontWeight: 600, padding: '4px 10px', borderRadius: '6px',
                  border: '1px solid var(--color-border)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                  background: groupByCategory ? 'var(--color-accent)' : 'var(--color-bg-elevated)',
                  color: groupByCategory ? 'white' : 'var(--color-text-secondary)',
                  marginRight: '12px', transition: 'all 0.15s',
                }}
              >
                <Filter style={{ width: '12px', height: '12px' }} />
                Grouped
              </button>
              {['', 'critical', 'high', 'medium', 'low'].map(sev => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  style={{
                    fontSize: '11px', fontWeight: 500, padding: '4px 10px', borderRadius: '6px',
                    border: '1px solid var(--color-border)', cursor: 'pointer',
                    background: severityFilter === sev ? 'var(--color-accent)' : 'var(--color-bg-elevated)',
                    color: severityFilter === sev ? 'white' : 'var(--color-text-secondary)',
                    transition: 'all 0.15s',
                  }}
                >
                  {sev ? (severityConfig[sev]?.icon + ' ' + severityConfig[sev]?.label) : 'All'}
                </button>
              ))}
            </div>
          </div>

          {/* Issues list */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
            {issuesLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '30px' }}>
                <Loader2 style={{ width: '24px', height: '24px', color: 'var(--color-accent)', animation: 'spin 1s linear infinite' }} />
              </div>
            ) : issues.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-muted)' }}>
                {isAnalyzing ? (
                  <>
                    <Loader2 style={{ width: '28px', height: '28px', color: 'var(--color-accent)', animation: 'spin 1s linear infinite', margin: '0 auto 12px' }} />
                    <p style={{ fontSize: '14px', fontWeight: 500 }}>🔍 AI is deeply analyzing your repository...</p>
                    <p style={{ fontSize: '12px', marginTop: '4px' }}>Running 3-phase analysis: bug detection → improvements → architecture review</p>
                    <p style={{ fontSize: '11px', marginTop: '2px', opacity: 0.7 }}>This can take 1-3 minutes for large codebases</p>
                  </>
                ) : summary?.analysis_status === 'analyzed' ? (
                  <>
                    <p style={{ fontSize: '16px', fontWeight: 600, color: '#10b981' }}>✅ No critical bugs found</p>
                    {(summary?.improvement_count > 0 || summary?.type_breakdown?.improvement > 0) ? (
                      <p style={{ fontSize: '13px', marginTop: '8px', color: '#f59e0b' }}>
                        💡 However, I found {summary?.improvement_count || summary?.type_breakdown?.improvement || 0} improvements to strengthen your code
                      </p>
                    ) : null}
                    <p style={{ fontSize: '12px', marginTop: '6px', opacity: 0.7 }}>
                      {(severityFilter || selectedFile)
                        ? 'Try clearing filters to see all findings.'
                        : 'Your code passed strict AI analysis. Great work!'
                      }
                    </p>
                  </>
                ) : summary?.analysis_status === 'failed' ? (
                  <>
                    <p style={{ fontSize: '14px', fontWeight: 500, color: '#ef4444' }}>❌ Analysis failed</p>
                    <p style={{ fontSize: '12px', marginTop: '6px' }}>{summary?.summary_message || 'Please try re-indexing the repository.'}</p>
                  </>
                ) : (
                  <p style={{ fontSize: '14px' }}>Analysis pending — index the repository to start</p>
                )}
              </div>
            ) : (
              (() => {
                const renderIssueCard = (issue) => {
                  const sev = severityConfig[issue.severity] || severityConfig.medium
                  const TypeIcon = typeIcons[issue.issue_type] || AlertTriangle
                  const isExpanded = expandedIssue === issue.id
                  
                  let confIcon = '❓'
                  if (issue.confidence_score >= 0.8) confIcon = '🔥'
                  else if (issue.confidence_score >= 0.5) confIcon = '⚠️'

                  return (
                    <div
                      key={issue.id}
                      onClick={() => setExpandedIssue(isExpanded ? null : issue.id)}
                      style={{
                        padding: '12px 14px', borderRadius: '8px', marginBottom: '6px', cursor: 'pointer',
                        border: `1px solid ${isExpanded ? 'var(--color-accent)' : 'var(--color-border)'}`,
                        background: isExpanded ? 'rgba(139,92,246,0.04)' : 'var(--color-bg-elevated)',
                        transition: 'all 0.15s',
                      }}
                    >
                      {/* Issue header */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {isExpanded ? (
                          <ChevronDown style={{ width: '14px', height: '14px', color: 'var(--color-text-muted)', flexShrink: 0 }} />
                        ) : (
                          <ChevronRight style={{ width: '14px', height: '14px', color: 'var(--color-text-muted)', flexShrink: 0 }} />
                        )}
                        <TypeIcon style={{ width: '14px', height: '14px', color: sev.color, flexShrink: 0 }} strokeWidth={1.5} />
                        <span style={{ flex: 1, fontSize: '13px', fontWeight: 500, color: 'var(--color-text-primary)' }}>
                          {issue.title}
                        </span>
                        <span style={{
                          fontSize: '10px', fontWeight: 700, padding: '3px 8px', borderRadius: '4px',
                          background: sev.bg, color: sev.color, textTransform: 'uppercase',
                        }}>
                          {sev.label}
                        </span>
                        <span style={{
                          fontSize: '11px', fontWeight: 600, padding: '2px 6px', borderRadius: '4px',
                          background: 'rgba(59,130,246,0.1)', color: '#3b82f6',
                        }}>
                          ★ {issue.priority_score?.toFixed(1) || '0.0'}
                        </span>
                      </div>

                      {/* Expanded content */}
                      {isExpanded && (
                        <div style={{ marginTop: '12px', paddingLeft: '38px' }}>
                          <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '10px' }}>
                            📁 {issue.file_path}
                            {issue.line_start && ` : L${issue.line_start}`}
                            {issue.line_end && `-${issue.line_end}`}
                            <span style={{ marginLeft: '12px', color: 'var(--color-text-secondary)', background: 'var(--color-bg-card)', padding: '2px 6px', borderRadius: '4px' }}>
                              {confIcon} Confidence: {Math.round(issue.confidence_score * 100)}%
                            </span>
                          </p>
                          
                          <div style={{
                            padding: '12px', borderRadius: '8px', marginBottom: '10px',
                            background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
                          }}>
                            <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: '6px' }}>
                              Description
                            </p>
                            <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: '1.6' }}>
                              {issue.description}
                            </p>
                          </div>

                          {(issue.impact || issue.why_it_matters) && (
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '10px' }}>
                              <div style={{ padding: '12px', borderRadius: '8px', background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.1)' }}>
                                <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, color: '#ef4444', marginBottom: '6px' }}>
                                  What can go wrong
                                </p>
                                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: '1.5' }}>{issue.impact}</p>
                              </div>
                              <div style={{ padding: '12px', borderRadius: '8px', background: 'rgba(245,158,11,0.04)', border: '1px solid rgba(245,158,11,0.1)' }}>
                                <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, color: '#f59e0b', marginBottom: '6px' }}>
                                  Real-world consequence
                                </p>
                                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: '1.5' }}>{issue.why_it_matters}</p>
                              </div>
                            </div>
                          )}

                          {issue.fix_suggestion && (
                            <div style={{
                              padding: '12px', borderRadius: '8px',
                              background: 'rgba(16,185,129,0.05)', border: '1px solid rgba(16,185,129,0.15)',
                            }}>
                              <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, color: '#10b981', marginBottom: '6px' }}>
                                💡 Suggested Fix
                              </p>
                              <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: '1.6', fontFamily: 'var(--font-mono)' }}>
                                {issue.fix_suggestion}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                }

                if (!groupByCategory) {
                  return issues.map(renderIssueCard)
                }

                // Grouped rendering
                const grouped = issues.reduce((acc, issue) => {
                  const cat = issue.category || 'Other'
                  if (!acc[cat]) acc[cat] = []
                  acc[cat].push(issue)
                  return acc
                }, {})

                return Object.entries(grouped).map(([category, catIssues]) => (
                  <div key={category} style={{ marginBottom: '16px' }}>
                    <h4 style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', padding: '0 4px', marginBottom: '8px' }}>
                      {category} <span style={{ opacity: 0.7, fontWeight: 500 }}>({catIssues.length})</span>
                    </h4>
                    {catIssues.map(renderIssueCard)}
                  </div>
                ))
              })()
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
