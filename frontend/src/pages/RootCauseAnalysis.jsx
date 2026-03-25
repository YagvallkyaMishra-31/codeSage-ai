import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { 
  Copy, CheckCircle, ExternalLink, AlertTriangle, ChevronRight, FileCode, 
  Check, MessageSquare, Terminal, RefreshCw, Layers, Search, Loader2 
} from 'lucide-react'

import { searchAPI } from '../services/api'

export default function RootCauseAnalysis() {
  const location = useLocation()
  const initialResult = location.state?.result
  const initialError = location.state?.errorText

  const [searchQuery, setSearchQuery] = useState(initialError || '')
  const [result, setResult] = useState(initialResult || null)
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState('')

  const handleSearch = async (e) => {
    if (e) e.preventDefault()
    if (!searchQuery.trim()) return
    
    setIsSearching(true)
    setSearchError('')
    try {
      const res = await searchAPI.search({ query: searchQuery.trim(), top_k: 5 })
      
      setResult({
        ...result,
        searchResults: res.data.results
      })
    } catch (err) {
      setSearchError(err.response?.data?.detail || err.message)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div style={{ padding: '32px', height: '100%', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
      {/* ── Page Header ── */}
      <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.02em' }}>
            Root Cause Analysis
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
            AI-powered architectural diagnosis and remediation.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <form onSubmit={handleSearch} style={{ position: 'relative' }}>
            <Search style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', width: '16px', height: '16px', color: 'var(--color-text-muted)' }} />
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search code semantics..."
              style={{
                width: '300px', padding: '9px 12px 9px 38px', borderRadius: '10px', fontSize: '13px',
                background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
                color: 'var(--color-text-primary)', outline: 'none',
              }}
            />
            {isSearching && <Loader2 style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', width: '14px', height: '14px', color: 'var(--color-accent)' }} className="animate-spin" />}
          </form>
          {result && (
            <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                padding: '8px 16px', borderRadius: '10px', fontSize: '13px', fontWeight: 600,
                background: 'rgba(16,185,129,0.1)', color: '#10b981', border: '1px solid rgba(16,185,129,0.2)'
              }}>
                <CheckCircle style={{ width: '15px', height: '15px' }} strokeWidth={2} /> Analysis Ready
              </span>
          )}
        </div>
      </div>

      {/* ── Main Layout ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 340px', gap: '24px', flex: 1, minHeight: 0 }}>
        
        {/* ── Left: Issue Details & Code Fix ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', minHeight: 0, overflowY: 'auto', paddingRight: '12px' }}>
          
          {result?.root_cause ? (
            <>
              {/* Issue Breakdown Card */}
              <div style={{
                background: 'var(--color-bg-card)',
                border: '1px solid var(--color-border)',
                borderRadius: '14px',
                padding: '28px',
                flexShrink: 0,
                boxShadow: '0 4px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  {/* Issue */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <div style={{ width: '24px', height: '24px', borderRadius: '6px', background: 'rgba(239,68,68,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <AlertTriangle style={{ width: '12px', height: '12px', color: '#ef4444' }} strokeWidth={2.5} />
                      </div>
                      <h2 style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)' }}>Detected Issue</h2>
                    </div>
                    <p style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {result.category || 'Debug Analysis'}: <span style={{ fontFamily: 'var(--font-mono)', background: 'rgba(239,68,68,0.1)', color: '#ef4444', padding: '2px 8px', borderRadius: '6px', fontSize: '15px' }}>{result.file_path || 'Repository'}</span>
                    </p>
                  </div>

                  <div style={{ height: '1px', background: 'var(--color-border)' }} />

                  {/* Cause */}
                  <div>
                    <h2 style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)', marginBottom: '8px' }}>Root Cause</h2>
                    <p style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '8px' }}>{result.root_cause}</p>
                    <p style={{ fontSize: '14px', lineHeight: '1.7', color: 'var(--color-text-secondary)', maxWidth: '90%' }}>
                      {result.explanation}
                    </p>
                  </div>

                  {/* Impact */}
                  <div style={{
                    background: 'rgba(245,158,11,0.05)',
                    border: '1px solid rgba(245,158,11,0.2)',
                    borderRadius: '12px',
                    padding: '20px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                      <span style={{ fontSize: '16px' }}>⚠️</span>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: '#f59e0b' }}>{result.severity?.toUpperCase() || 'MEDIUM'} Severity Impact</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {(result.impact_points || [
                        'Potential runtime instability',
                        'Increased resource consumption',
                        'Degraded user experience'
                      ]).map((impact, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                          <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#f59e0b', marginTop: '7px', flexShrink: 0 }} />
                          <p style={{ fontSize: '13px', lineHeight: '1.5', color: 'var(--color-text-secondary)' }}>{impact}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Code Fix Editor */}
              <div style={{
                background: 'var(--color-bg-card)',
                border: '1px solid var(--color-border)',
                borderRadius: '14px',
                flexShrink: 0,
                boxShadow: '0 4px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
                display: 'flex', flexDirection: 'column', overflow: 'hidden',
              }}>
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '12px 20px', background: 'var(--color-bg-elevated)', borderBottom: '1px solid var(--color-border)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                     <Terminal style={{ width: '16px', height: '16px', color: 'var(--color-text-muted)' }} />
                     <span style={{ fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>{result.file_path || 'suggested_fix.patch'}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '12px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle style={{ width: '12px', height: '12px' }} /> AI Suggested
                    </span>
                    <button style={{
                      display: 'flex', alignItems: 'center', gap: '6px',
                      background: 'transparent', border: 'none', color: 'var(--color-text-muted)',
                      fontSize: '12px', fontWeight: 500, cursor: 'pointer',
                    }} onClick={() => navigator.clipboard.writeText(result.code_patch)}>
                      <Copy style={{ width: '14px', height: '14px' }} /> Copy Fix
                    </button>
                  </div>
                </div>
                <div style={{ background: '#0d0d0f', padding: '16px 24px', fontFamily: 'var(--font-mono)', fontSize: '13.5px', lineHeight: '1.6', overflowX: 'auto' }}>
                  <pre style={{ margin: 0, color: '#10b981' }}>
                    {result.code_patch || result.suggested_fix}
                  </pre>
                </div>
                <div style={{ padding: '16px 20px', background: 'var(--color-bg-card)', borderTop: '1px solid var(--color-border)' }}>
                   <p style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>Verify changes before applying to production.</p>
                </div>
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {!result?.searchResults && (
                <div style={{
                  flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'var(--color-bg-card)', border: '1px dashed var(--color-border)', borderRadius: '14px', minHeight: '300px'
                }}>
                  <div style={{ textAlign: 'center', maxWidth: '300px' }}>
                    <Search style={{ width: '40px', height: '40px', color: 'var(--color-text-muted)', margin: '0 auto 16px' }} />
                    <p style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: '8px' }}>No Active Analysis</p>
                    <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', lineHeight: '1.5' }}>
                      Use the search bar above or submit an issue in the <strong>Debug Assistant</strong> to see results.
                    </p>
                  </div>
                </div>
              )}

              {result?.searchResults && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>Semantic Code Results</h3>
                  {result.searchResults.map((r, i) => (
                    <div key={i} style={{
                      background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '12px', padding: '20px',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <FileCode style={{ width: '16px', height: '16px', color: 'var(--color-accent)' }} />
                          <span style={{ fontSize: '14px', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{r.file_path}</span>
                        </div>
                        <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Match Score: {Math.round(r.score * 100)}%</span>
                      </div>
                      <pre style={{
                        background: '#0d0d0f', padding: '12px', borderRadius: '8px', fontSize: '12px', fontFamily: 'var(--font-mono)',
                        color: 'var(--color-text-secondary)', overflowX: 'auto', border: '1px solid var(--color-border)',
                      }}>
                        {r.chunk_text}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Right: Sidebar ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', minHeight: 0 }}>
          <h3 style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)' }}>
            Verification & Context
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { icon: Layers, label: 'View Trace Graph', color: '#3b82f6' },
              { icon: MessageSquare, label: 'Chat with Assistant', color: '#10b981' },
              { icon: ExternalLink, label: 'Open in Repository', color: '#a855f7' }
            ].map(link => (
              <button key={link.label} style={{
                display: 'flex', alignItems: 'center', gap: '12px', padding: '14px', borderRadius: '12px',
                background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
                color: 'var(--color-text-secondary)', fontSize: '13px', fontWeight: 500, cursor: 'pointer',
              }}>
                <link.icon style={{ width: '16px', height: '16px', color: link.color }} />
                {link.label}
              </button>
            ))}
          </div>

          {result?.context_used && (
            <div style={{
              background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: '14px', padding: '20px',
            }}>
              <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '16px' }}>Context Used</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {result.context_used.map((ctx, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ width: '6px', height: '1px', background: 'var(--color-border)' }} />
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {ctx.file_path}
                      </p>
                      <p style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>Score: {Math.round(ctx.score * 100)}%</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
