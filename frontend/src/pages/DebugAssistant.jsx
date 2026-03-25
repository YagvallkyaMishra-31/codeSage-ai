import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload, Sparkles, Terminal, Globe, AlertTriangle, FileCode,
  MessageSquare, Settings, Play, CheckCircle2, Search, ArrowRight,
  Clock, Hash, Loader2
} from 'lucide-react'

import { debugAPI } from '../services/api'

const recentQueries = [
  { label: 'React Hook "useContext" is called conditionally', time: '14m ago', status: 'Root cause found', type: 'React' },
  { label: 'Connection timeout in pg-pool', time: '3h ago', status: 'Suggestion applied', type: 'Database' },
  { label: 'Memory leak in Docker container', time: '5h ago', status: 'Investigating', type: 'Infrastructure' },
  { label: 'Uncaught TypeError: map is not a function', time: 'Yesterday', status: 'Resolved', type: 'JavaScript' },
]

const capabilities = [
  { icon: AlertTriangle, label: 'Stack traces', desc: 'Identify root cause from error stacks', color: '#ef4444' },
  { icon: Terminal, label: 'Runtime errors', desc: 'Debug execution failures', color: '#f59e0b' },
  { icon: FileCode, label: 'Console logs', desc: 'Analyze log patterns', color: '#3b82f6' },
  { icon: Globe, label: 'Code snippets', desc: 'Review code for bugs', color: '#8b5cf6' },
]

export default function DebugAssistant() {
  const [codeInput, setCodeInput] = useState('')
  const [activeTab, setActiveTab] = useState('input')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleAnalyze = async () => {
    if (!codeInput.trim()) return
    setIsAnalyzing(true)
    setError('')
    
    try {
      const res = await debugAPI.analyze({ error: codeInput.trim() })
      
      // Navigate to analysis page with the result
      navigate('/analysis', { state: { result: res.data, errorText: codeInput } })
    } catch (err) {
      console.error('Analysis error:', err)
      setError(err.response?.data?.detail || err.message)
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div style={{ padding: '32px', height: '100%', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
      {/* ── Page Header ── */}
      <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.02em' }}>
            Debug Assistant
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
            Paste logs, stack traces, or problematic code to identify the root cause instantly.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '9px 18px', borderRadius: '10px', fontSize: '13px', fontWeight: 600,
            background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
            color: 'var(--color-text-secondary)', cursor: 'pointer', transition: 'all 0.15s ease',
          }}>
            <MessageSquare style={{ width: '15px', height: '15px' }} /> History
          </button>
          <button style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '9px 18px', borderRadius: '10px', fontSize: '13px', fontWeight: 600,
            background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
            color: 'var(--color-text-secondary)', cursor: 'pointer', transition: 'all 0.15s ease',
          }}>
            <Settings style={{ width: '15px', height: '15px' }} /> Settings
          </button>
        </div>
      </div>

      {/* ── Main Layout ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px', flex: 1, minHeight: 0 }}>
        
        {/* ── Left: Main Editor ── */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{
            flex: 1,
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-border)',
            borderRadius: '14px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}>
            {/* Editor Top Chrome */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px', background: 'var(--color-bg-elevated)',
              borderBottom: '1px solid var(--color-border)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                {/* Traffic Lights */}
                <div style={{ display: 'flex', gap: '6px' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#ff5f56', border: '1px solid #e0443e' }} />
                  <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#ffbd2e', border: '1px solid #dea123' }} />
                  <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#27c93f', border: '1px solid #1aab29' }} />
                </div>
                {/* Tabs */}
                <div style={{ display: 'flex', gap: '4px' }}>
                  {['input', 'context', 'terminal'].map(tab => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      style={{
                        padding: '6px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 600,
                        fontFamily: 'var(--font-mono)', textTransform: 'lowercase',
                        background: activeTab === tab ? 'var(--color-bg-card)' : 'transparent',
                        color: activeTab === tab ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                        border: 'none', cursor: 'pointer', transition: 'all 0.15s ease',
                      }}
                    >
                      {tab}
                    </button>
                  ))}
                </div>
              </div>
              <button style={{
                fontSize: '12px', fontWeight: 500, color: 'var(--color-text-muted)',
                background: 'transparent', border: 'none', cursor: 'pointer',
              }} onClick={() => setCodeInput('')}>
                Clear All
              </button>
            </div>

            {/* Textarea Area */}
            <div style={{ flex: 1, position: 'relative', display: 'flex', background: '#0d0d0f' }}>
              {/* Fake line numbers column */}
              <div style={{
                width: '48px', padding: '24px 0', borderRight: '1px solid var(--color-border)',
                background: 'rgba(255,255,255,0.02)', display: 'flex', flexDirection: 'column',
                alignItems: 'center', gap: '8px',
              }}>
                {[1, 2, 3, 4, 5, 6].map(n => (
                  <span key={n} style={{ fontSize: '13px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)', opacity: 0.3, lineHeight: '1.8' }}>
                    {n}
                  </span>
                ))}
              </div>
              
            <textarea
                value={codeInput}
                onChange={(e) => setCodeInput(e.target.value)}
                placeholder={`TypeError: Cannot read property 'map' of undefined\n    at UserList.tsx:34\n    at renderWithHooks (react-dom.development.js:14985)\n    at mountIndeterminateComponent (react-dom.development.js:17811)\n\nPaste your stack trace, error log, or code snippet here...`}
                disabled={isAnalyzing}
                style={{
                  flex: 1, padding: '24px', fontSize: '14px', fontFamily: 'var(--font-mono)',
                  color: 'var(--color-text-secondary)', background: 'transparent',
                  border: 'none', outline: 'none', resize: 'none', lineHeight: '1.8',
                  opacity: isAnalyzing ? 0.6 : 1,
                }}
                spellCheck="false"
              />
              {error && (
                <div style={{
                  position: 'absolute', bottom: '20px', left: '20px', right: '20px',
                  padding: '12px 16px', borderRadius: '8px', background: 'rgba(239,68,68,0.1)',
                  border: '1px solid rgba(239,68,68,0.2)', color: '#ef4444', fontSize: '13px',
                  display: 'flex', alignItems: 'flex-start', gap: '8px', zIndex: 10,
                  maxHeight: '80px', overflowY: 'auto',
                }}>
                  <AlertTriangle style={{ width: '16px', height: '16px', flexShrink: 0, marginTop: '2px' }} />
                  <span style={{ wordBreak: 'break-word', overflow: 'hidden', lineHeight: '1.4' }}>{error}</span>
                </div>
              )}
            </div>

            {/* Bottom Actions Chrome */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '16px 20px', background: 'var(--color-bg-card)',
              borderTop: '1px solid var(--color-border)',
            }}>
              <button style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '10px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: 600,
                background: 'var(--color-bg-elevated)', border: '1px dashed var(--color-border)',
                color: 'var(--color-text-secondary)', cursor: isAnalyzing ? 'not-allowed' : 'pointer', transition: 'all 0.15s ease',
              }} disabled={isAnalyzing}>
                <Upload style={{ width: '15px', height: '15px', color: 'var(--color-text-muted)' }} />
                Upload Screenshot or Log File
              </button>
              
              <button 
                onClick={handleAnalyze}
                disabled={isAnalyzing || !codeInput.trim()}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '10px 24px', borderRadius: '8px', fontSize: '14px', fontWeight: 600,
                  background: isAnalyzing ? 'var(--color-bg-elevated)' : 'var(--color-accent)', border: 'none',
                  color: isAnalyzing ? 'var(--color-text-muted)' : 'white', cursor: isAnalyzing || !codeInput.trim() ? 'not-allowed' : 'pointer', transition: 'all 0.15s ease',
                  boxShadow: isAnalyzing ? 'none' : '0 4px 14px rgba(139, 92, 246, 0.4)',
                }}
              >
                {isAnalyzing ? (
                  <Loader2 style={{ width: '16px', height: '16px' }} className="animate-spin" />
                ) : (
                  <Sparkles style={{ width: '16px', height: '16px' }} />
                )}
                {isAnalyzing ? 'Analyzing...' : 'Analyze Issue'}
              </button>
            </div>
          </div>
        </div>

        {/* ── Right: Capabilities & History ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', minHeight: 0 }}>
          
          {/* AI Capabilities Card */}
          <div style={{
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-border)',
            borderRadius: '14px',
            padding: '22px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
          }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '16px' }}>
              Analysis Capabilities
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {capabilities.map((cap) => (
                <div key={cap.label} style={{
                  display: 'flex', alignItems: 'center', gap: '14px',
                  padding: '12px', borderRadius: '10px',
                  background: 'var(--color-bg-elevated)',
                  border: '1px solid transparent', transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--color-border)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'transparent'}
                >
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '10px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: `${cap.color}15`, flexShrink: 0,
                  }}>
                    <cap.icon style={{ width: '18px', height: '18px', color: cap.color }} strokeWidth={1.5} />
                  </div>
                  <div>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '2px' }}>{cap.label}</p>
                    <p style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>{cap.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Queries Card */}
          <div style={{
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-border)',
            borderRadius: '14px',
            padding: '22px',
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
            overflow: 'hidden',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                Recent Queries
              </h3>
              <Search style={{ width: '15px', height: '15px', color: 'var(--color-text-muted)' }} />
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
              {recentQueries.map((q, i) => (
                <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '6px', cursor: 'pointer' }}
                     className="group">
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
                    <p style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text-primary)', lineHeight: '1.4' }}
                       className="group-hover:text-[var(--color-accent)] transition-colors">
                      {q.label}
                    </p>
                    <ArrowRight style={{ width: '14px', height: '14px', color: 'var(--color-text-muted)', opacity: 0 }}
                                className="group-hover:opacity-100 transition-opacity" />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{
                      fontSize: '10px', fontWeight: 600, padding: '2px 6px', borderRadius: '4px',
                      background: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)',
                    }}>
                      {q.type}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle2 style={{ width: '10px', height: '10px' }} /> {q.status}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>• {q.time}</span>
                  </div>
                  {i < recentQueries.length - 1 && (
                    <div style={{ height: '1px', background: 'var(--color-border)', marginTop: '10px' }} />
                  )}
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
