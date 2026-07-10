import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Database, Cpu, Globe, Key, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react'

export default function SettingsPage() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`)
        const data = await res.json()
        setStatus(data)
      } catch {
        setStatus({ error: true })
      } finally {
        setLoading(false)
      }
    }
    checkHealth()
  }, [])

  const cardStyle = {
    background: 'var(--color-bg-card)', borderRadius: '14px',
    border: '1px solid var(--color-border)', padding: '24px', marginBottom: '16px',
  }

  const labelStyle = {
    fontSize: '11px', fontWeight: 700, textTransform: 'uppercase',
    letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: '6px',
  }

  const valueStyle = {
    fontSize: '14px', fontWeight: 500, color: 'var(--color-text-primary)',
  }

  const configItems = [
    { label: 'Backend URL', value: import.meta.env.VITE_API_URL || 'http://localhost:8000', icon: Globe },
    { label: 'Database', value: 'SQLite (Local)', icon: Database },
    { label: 'LLM Provider', value: 'Groq (llama-3.3-70b-versatile)', icon: Cpu },
    { label: 'Embedding Model', value: 'all-MiniLM-L6-v2', icon: Key },
    { label: 'Vector Store', value: 'FAISS (Local)', icon: Database },
  ]

  return (
    <div style={{ padding: '32px', maxWidth: '800px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '32px' }}>
        <div style={{
          width: '42px', height: '42px', borderRadius: '12px',
          background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(109,40,217,0.2))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <SettingsIcon style={{ width: '22px', height: '22px', color: '#8b5cf6' }} />
        </div>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-text-primary)' }}>Settings</h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>System configuration and health status</p>
        </div>
      </div>

      {/* Health Status */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          {loading ? (
            <RefreshCw style={{ width: '18px', height: '18px', color: '#f59e0b', animation: 'spin 1s linear infinite' }} />
          ) : status?.error ? (
            <AlertCircle style={{ width: '18px', height: '18px', color: '#ef4444' }} />
          ) : (
            <CheckCircle2 style={{ width: '18px', height: '18px', color: '#10b981' }} />
          )}
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            System Health
          </h2>
          <span style={{
            fontSize: '11px', fontWeight: 600, padding: '3px 10px', borderRadius: '6px',
            background: loading ? 'rgba(245,158,11,0.1)' : status?.error ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
            color: loading ? '#f59e0b' : status?.error ? '#ef4444' : '#10b981',
          }}>
            {loading ? 'Checking...' : status?.error ? 'Offline' : 'Online'}
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <p style={labelStyle}>Backend API</p>
            <p style={valueStyle}>{status?.error ? 'Unreachable' : 'Connected'}</p>
          </div>
          <div>
            <p style={labelStyle}>Server Status</p>
            <p style={valueStyle}>{status?.status || 'Unknown'}</p>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div style={cardStyle}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '20px' }}>
          Configuration
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {configItems.map((item) => {
            const Icon = item.icon
            return (
              <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div style={{
                  width: '34px', height: '34px', borderRadius: '8px',
                  background: 'var(--color-bg-elevated)', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <Icon style={{ width: '16px', height: '16px', color: '#8b5cf6' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <p style={labelStyle}>{item.label}</p>
                  <p style={{
                    ...valueStyle, fontFamily: 'var(--font-mono)', fontSize: '13px',
                    color: 'var(--color-text-secondary)',
                  }}>{item.value}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* About */}
      <div style={cardStyle}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '12px' }}>
          About CodeSage AI
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', lineHeight: 1.7 }}>
          CodeSage AI is an intelligent code analysis and debugging assistant that uses
          RAG (Retrieval-Augmented Generation) to provide context-aware insights about your codebase.
          It uses FAISS for vector search, SentenceTransformers for embeddings, and Groq's LLM API
          for AI-powered analysis.
        </p>
        <div style={{ marginTop: '14px', display: 'flex', gap: '8px' }}>
          {['FastAPI', 'React', 'FAISS', 'Groq', 'SentenceTransformers'].map(t => (
            <span key={t} style={{
              fontSize: '11px', padding: '3px 10px', borderRadius: '6px',
              background: 'rgba(139,92,246,0.1)', color: '#a78bfa', fontWeight: 600,
            }}>{t}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
