import { useState, useEffect, useRef } from 'react'
import {
  Send, Bot, User, FileCode, Loader2, Sparkles, ChevronDown,
  Code2, Trash2, FolderGit2, AlertCircle
} from 'lucide-react'
import { chatAPI, repositoryAPI } from '../services/api'

// Simple markdown-to-JSX renderer for code blocks and formatting
function renderMarkdown(text) {
  if (!text) return null

  const parts = text.split(/(```[\s\S]*?```)/g)

  return parts.map((part, i) => {
    // Code blocks
    if (part.startsWith('```')) {
      const lines = part.split('\n')
      const lang = lines[0].replace('```', '').trim()
      const code = lines.slice(1, -1).join('\n')
      return (
        <div key={i} style={{
          margin: '12px 0', borderRadius: '8px', overflow: 'hidden',
          border: '1px solid rgba(255,255,255,0.08)',
        }}>
          {lang && (
            <div style={{
              padding: '6px 12px', fontSize: '11px', fontWeight: 600,
              background: 'rgba(139,92,246,0.15)', color: '#a78bfa',
              fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}>
              {lang}
            </div>
          )}
          <pre style={{
            margin: 0, padding: '14px 16px', fontSize: '12.5px',
            fontFamily: 'var(--font-mono)', background: '#0a0a0c',
            color: '#e4e4e7', lineHeight: 1.7, overflowX: 'auto',
            whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          }}>
            {code}
          </pre>
        </div>
      )
    }

    // Inline formatting
    return (
      <span key={i}>
        {part.split('\n').map((line, j) => {
          // Bold
          let formatted = line.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
          // Inline code
          formatted = formatted.replace(/`([^`]+)`/g,
            '<code style="background:rgba(139,92,246,0.12);padding:1px 6px;border-radius:4px;font-family:var(--font-mono);font-size:12px;color:#c4b5fd">$1</code>')
          // File paths (bold them)
          formatted = formatted.replace(/\[(\d+)\]/g, '<sup style="color:#8b5cf6;font-weight:700">[$1]</sup>')

          return (
            <span key={j}>
              {j > 0 && <br />}
              <span dangerouslySetInnerHTML={{ __html: formatted }} />
            </span>
          )
        })}
      </span>
    )
  })
}


const suggestedQuestions = [
  "What does this codebase do?",
  "What are the main API endpoints?",
  "How is authentication handled?",
  "Find potential security issues",
  "Explain the database schema",
  "What dependencies does this project use?",
]


export default function DebugAssistant() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [repos, setRepos] = useState([])
  const [selectedRepo, setSelectedRepo] = useState(null)
  const [showRepoDropdown, setShowRepoDropdown] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Load repos on mount
  useEffect(() => {
    const loadRepos = async () => {
      try {
        const res = await repositoryAPI.list()
        const repoList = res.data.repositories || []
        setRepos(repoList)
        // Auto-select first completed repo
        const completed = repoList.find(r => r.status === 'completed')
        if (completed) setSelectedRepo(completed)
      } catch (err) {
        console.error('Failed to load repos:', err)
      }
    }
    loadRepos()
  }, [])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (text) => {
    const msg = (text || input).trim()
    if (!msg || isLoading) return

    const userMsg = { role: 'user', content: msg }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      const res = await chatAPI.ask({
        message: msg,
        repo_id: selectedRepo?.id || null,
        history: messages.slice(-6), // Last 6 messages for context
      })

      const assistantMsg = {
        role: 'assistant',
        content: res.data.reply,
        sources: res.data.sources || [],
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content: `⚠️ **Error**: ${err.response?.data?.detail || err.message || 'Failed to get response'}`,
        isError: true,
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  const selectedRepoName = selectedRepo?.name || 'All Repositories'

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--color-bg-primary)' }}>

      {/* ── Top Bar ── */}
      <div style={{
        padding: '14px 24px', borderBottom: '1px solid var(--color-border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'var(--color-bg-card)', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            background: 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Sparkles style={{ width: '18px', height: '18px', color: 'white' }} />
          </div>
          <div>
            <h1 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.01em' }}>
              CodeSage Chat
            </h1>
            <p style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              RAG-powered AI assistant for your codebase
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {/* Repo selector */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setShowRepoDropdown(!showRepoDropdown)}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '7px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 600,
                background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
                color: 'var(--color-text-secondary)', cursor: 'pointer', transition: 'all 0.15s',
              }}
            >
              <FolderGit2 style={{ width: '14px', height: '14px', color: '#8b5cf6' }} />
              {selectedRepoName}
              <ChevronDown style={{ width: '12px', height: '12px' }} />
            </button>
            {showRepoDropdown && (
              <div style={{
                position: 'absolute', top: '100%', right: 0, marginTop: '6px',
                background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
                borderRadius: '10px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                minWidth: '220px', zIndex: 100, overflow: 'hidden',
              }}>
                <button
                  onClick={() => { setSelectedRepo(null); setShowRepoDropdown(false) }}
                  style={{
                    width: '100%', textAlign: 'left', padding: '10px 14px', fontSize: '12px',
                    background: !selectedRepo ? 'var(--color-accent-subtle)' : 'transparent',
                    color: !selectedRepo ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                    border: 'none', cursor: 'pointer', fontWeight: 500,
                    borderBottom: '1px solid var(--color-border)',
                  }}
                >
                  All Repositories
                </button>
                {repos.filter(r => r.status === 'completed').map(r => (
                  <button
                    key={r.id}
                    onClick={() => { setSelectedRepo(r); setShowRepoDropdown(false) }}
                    style={{
                      width: '100%', textAlign: 'left', padding: '10px 14px', fontSize: '12px',
                      background: selectedRepo?.id === r.id ? 'var(--color-accent-subtle)' : 'transparent',
                      color: selectedRepo?.id === r.id ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                      border: 'none', borderBottom: '1px solid var(--color-border)',
                      cursor: 'pointer', fontWeight: 500,
                    }}
                  >
                    {r.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={clearChat}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '7px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 500,
              background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
              color: 'var(--color-text-muted)', cursor: 'pointer',
            }}
          >
            <Trash2 style={{ width: '13px', height: '13px' }} /> Clear
          </button>
        </div>
      </div>

      {/* ── Messages Area ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        {messages.length === 0 ? (
          /* ── Empty State ── */
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', gap: '28px',
          }}>
            <div style={{
              width: '72px', height: '72px', borderRadius: '20px',
              background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(109,40,217,0.2))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '1px solid rgba(139,92,246,0.2)',
            }}>
              <Bot style={{ width: '36px', height: '36px', color: '#8b5cf6' }} />
            </div>
            <div style={{ textAlign: 'center', maxWidth: '460px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '8px' }}>
                Ask me anything about your code
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
                I use RAG (Retrieval-Augmented Generation) to search your indexed repositories
                and answer questions with real code context.
                {selectedRepo && (
                  <span style={{ color: '#8b5cf6', fontWeight: 600 }}>
                    {' '}Currently focused on: {selectedRepo.name}
                  </span>
                )}
              </p>
            </div>

            {/* Suggested questions */}
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px',
              maxWidth: '520px', width: '100%',
            }}>
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(q)}
                  style={{
                    padding: '12px 16px', borderRadius: '10px', fontSize: '12.5px',
                    fontWeight: 500, textAlign: 'left', lineHeight: 1.4,
                    background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
                    color: 'var(--color-text-secondary)', cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'rgba(139,92,246,0.3)'
                    e.currentTarget.style.background = 'rgba(139,92,246,0.05)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'var(--color-border)'
                    e.currentTarget.style.background = 'var(--color-bg-card)'
                  }}
                >
                  <Sparkles style={{ width: '12px', height: '12px', color: '#8b5cf6', marginRight: '6px', verticalAlign: '-1px' }} />
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* ── Chat Messages ── */
          <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {messages.map((msg, i) => (
              <div key={i} style={{
                display: 'flex', gap: '12px',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              }}>
                {/* Avatar */}
                <div style={{
                  width: '32px', height: '32px', borderRadius: '10px', flexShrink: 0,
                  background: msg.role === 'user'
                    ? 'linear-gradient(135deg, #3b82f6, #2563eb)'
                    : 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {msg.role === 'user'
                    ? <User style={{ width: '16px', height: '16px', color: 'white' }} />
                    : <Bot style={{ width: '16px', height: '16px', color: 'white' }} />
                  }
                </div>

                {/* Message Bubble */}
                <div style={{
                  maxWidth: '75%',
                  padding: '14px 18px', borderRadius: '14px',
                  fontSize: '13.5px', lineHeight: 1.7,
                  background: msg.role === 'user'
                    ? 'linear-gradient(135deg, #3b82f6, #2563eb)'
                    : msg.isError
                      ? 'rgba(239,68,68,0.1)'
                      : 'var(--color-bg-card)',
                  color: msg.role === 'user' ? 'white' : 'var(--color-text-secondary)',
                  border: msg.role === 'user' ? 'none' : `1px solid ${msg.isError ? 'rgba(239,68,68,0.2)' : 'var(--color-border)'}`,
                  boxShadow: msg.role === 'user'
                    ? '0 4px 12px rgba(59,130,246,0.3)'
                    : '0 2px 8px rgba(0,0,0,0.2)',
                }}>
                  {renderMarkdown(msg.content)}

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{
                      marginTop: '14px', paddingTop: '12px',
                      borderTop: '1px solid var(--color-border)',
                    }}>
                      <p style={{
                        fontSize: '10px', fontWeight: 700, textTransform: 'uppercase',
                        letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: '8px',
                      }}>
                        <Code2 style={{ width: '11px', height: '11px', verticalAlign: '-1px', marginRight: '4px' }} />
                        Sources ({msg.sources.length} files)
                      </p>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {msg.sources.map((s, j) => (
                          <span key={j} style={{
                            fontSize: '11px', fontWeight: 500, padding: '3px 8px',
                            borderRadius: '6px', fontFamily: 'var(--font-mono)',
                            background: 'rgba(139,92,246,0.1)', color: '#a78bfa',
                            border: '1px solid rgba(139,92,246,0.15)',
                          }}>
                            <FileCode style={{ width: '10px', height: '10px', verticalAlign: '-1px', marginRight: '3px' }} />
                            {s.file_path}
                            <span style={{ opacity: 0.6, marginLeft: '4px' }}>
                              {Math.round(s.score * 100)}%
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isLoading && (
              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '10px', flexShrink: 0,
                  background: 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Bot style={{ width: '16px', height: '16px', color: 'white' }} />
                </div>
                <div style={{
                  padding: '14px 18px', borderRadius: '14px',
                  background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
                  display: 'flex', alignItems: 'center', gap: '8px',
                }}>
                  <Loader2 style={{ width: '16px', height: '16px', color: '#8b5cf6', animation: 'spin 1s linear infinite' }} />
                  <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
                    Searching code & generating response...
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* ── Input Bar ── */}
      <div style={{
        padding: '16px 24px', borderTop: '1px solid var(--color-border)',
        background: 'var(--color-bg-card)', flexShrink: 0,
      }}>
        <div style={{
          maxWidth: '800px', margin: '0 auto',
          display: 'flex', alignItems: 'flex-end', gap: '12px',
        }}>
          <div style={{
            flex: 1, display: 'flex', alignItems: 'flex-end',
            padding: '12px 16px', borderRadius: '14px',
            background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
            transition: 'border-color 0.15s',
          }}
            onFocus={() => {}}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={selectedRepo
                ? `Ask about ${selectedRepo.name}...`
                : "Ask about your codebase..."
              }
              disabled={isLoading}
              rows={1}
              style={{
                flex: 1, background: 'transparent', border: 'none', outline: 'none',
                fontSize: '14px', color: 'var(--color-text-primary)', resize: 'none',
                fontFamily: 'var(--font-sans)', lineHeight: 1.5,
                maxHeight: '120px', minHeight: '22px',
              }}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
              }}
            />
          </div>
          <button
            onClick={() => handleSend()}
            disabled={isLoading || !input.trim()}
            style={{
              width: '44px', height: '44px', borderRadius: '12px',
              background: isLoading || !input.trim()
                ? 'var(--color-bg-elevated)'
                : 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
              border: 'none', cursor: isLoading || !input.trim() ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.15s', flexShrink: 0,
              boxShadow: isLoading || !input.trim() ? 'none' : '0 4px 14px rgba(139,92,246,0.4)',
            }}
          >
            {isLoading
              ? <Loader2 style={{ width: '18px', height: '18px', color: 'var(--color-text-muted)', animation: 'spin 1s linear infinite' }} />
              : <Send style={{ width: '18px', height: '18px', color: isLoading || !input.trim() ? 'var(--color-text-muted)' : 'white' }} />
            }
          </button>
        </div>
        <p style={{ textAlign: 'center', fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '8px', opacity: 0.6 }}>
          CodeSage uses RAG to retrieve relevant code from your repositories before answering.
        </p>
      </div>
    </div>
  )
}
