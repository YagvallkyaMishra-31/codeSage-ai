import { useState, useEffect, useCallback } from 'react'
import { Search, Copy, Clock, AlertTriangle, Zap, GitBranch, Star, FileCode, Loader2 } from 'lucide-react'

import { activityAPI } from '../services/api'
const filters = ['All', 'ERROR', 'OPTIMIZATION', 'REFACTOR', 'FEATURE']

const typeStyles = {
  ERROR: { bg: 'rgba(239,68,68,0.1)', color: '#ef4444', icon: AlertTriangle, label: 'Error' },
  OPTIMIZATION: { bg: 'rgba(59,130,246,0.1)', color: '#3b82f6', icon: Zap, label: 'Optimization' },
  REFACTOR: { bg: 'rgba(168,85,247,0.1)', color: '#a855f7', icon: GitBranch, label: 'Refactor' },
  FEATURE: { bg: 'rgba(16,185,129,0.1)', color: '#10b981', icon: Star, label: 'Feature' },
}

export default function ActivityHistory() {
  const [activeFilter, setActiveFilter] = useState('All')
  const [activities, setActivities] = useState([])
  const [selectedActivity, setSelectedActivity] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  const fetchActivities = useCallback(async () => {
    setIsLoading(true)
    try {
      const params = activeFilter !== 'All' ? { category: activeFilter } : {}
      const res = await activityAPI.getAll({ ...params })
      const items = res.data.activities || []
      setActivities(items)
      if (items.length > 0 && !selectedActivity) {
        setSelectedActivity(items[0])
      }
    } catch (err) {
      console.error('Failed to fetch activities:', err)
    } finally {
      setIsLoading(false)
    }
  }, [activeFilter])

  useEffect(() => {
    fetchActivities()
  }, [fetchActivities])

  const filteredActivities = activities.filter(a => 
    a.error.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (a.root_cause && a.root_cause.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── Activity List Panel ── */}
      <div style={{
        width: '400px', flexShrink: 0, display: 'flex', flexDirection: 'column',
        background: 'var(--color-bg-sidebar)', borderRight: '1px solid var(--color-border)',
      }}>
        {/* Panel Header */}
        <div style={{ padding: '24px 20px 20px', borderBottom: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.02em' }}>
              Activity
            </h1>
            <span style={{
              fontSize: '11px', fontWeight: 600, padding: '4px 10px', borderRadius: '8px',
              background: 'var(--color-accent-subtle)', color: 'var(--color-accent)',
            }}>
              {activities.length} events
            </span>
          </div>

          {/* Search */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '10px 14px', borderRadius: '10px', marginBottom: '14px',
            background: 'var(--color-bg-input)', border: '1px solid var(--color-border)',
          }}>
            <Search style={{ width: '16px', height: '16px', color: 'var(--color-text-muted)' }} strokeWidth={1.5} />
            <input
              type="text"
              placeholder="Search activity..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: 'transparent', border: 'none', outline: 'none', width: '100%',
                fontSize: '13px', color: 'var(--color-text-primary)',
              }}
            />
          </div>

          {/* Filter Pills */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {filters.map((f) => (
              <button
                key={f}
                onClick={() => setActiveFilter(f)}
                style={{
                  padding: '6px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 600,
                  cursor: 'pointer', transition: 'all 0.15s ease', border: 'none',
                  background: activeFilter === f ? 'var(--color-accent)' : 'var(--color-bg-elevated)',
                  color: activeFilter === f ? 'white' : 'var(--color-text-secondary)',
                }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Activity Items */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {isLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
              <Loader2 className="animate-spin" style={{ color: 'var(--color-accent)' }} />
            </div>
          ) : filteredActivities.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
              No activities found.
            </div>
          ) : (
            filteredActivities.map((a) => {
              const style = typeStyles[a.category] || typeStyles.ERROR
              const Icon = style.icon
              const isSelected = selectedActivity?.id === a.id
              return (
                <div
                  key={a.id}
                  onClick={() => setSelectedActivity(a)}
                  style={{
                    padding: '16px 20px', cursor: 'pointer', transition: 'all 0.15s ease',
                    borderBottom: '1px solid var(--color-border)',
                    borderLeft: isSelected ? `3px solid var(--color-accent)` : '3px solid transparent',
                    background: isSelected ? 'var(--color-bg-card)' : 'transparent',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{
                        width: '24px', height: '24px', borderRadius: '6px',
                        background: style.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        <Icon style={{ width: '12px', height: '12px', color: style.color }} strokeWidth={2} />
                      </div>
                      <span style={{
                        fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em',
                        padding: '2px 8px', borderRadius: '4px', background: style.bg, color: style.color,
                      }}>
                        {a.category}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock style={{ width: '10px', height: '10px', color: 'var(--color-text-muted)' }} />
                      <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                        {new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                  <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>{a.error}</p>
                  <div style={{
                    display: 'inline-flex', alignItems: 'center', gap: '6px',
                    fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)',
                    background: 'var(--color-bg-elevated)', padding: '2px 8px', borderRadius: '4px',
                    marginBottom: '6px',
                  }}>
                    <FileCode style={{ width: '10px', height: '10px' }} />
                    {a.file_path || 'unknown'}
                  </div>
                  <p style={{ fontSize: '12px', lineHeight: '1.5', color: 'var(--color-text-muted)', marginTop: '4px' }}>{a.root_cause}</p>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* ── Details Panel ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
        {selectedActivity ? (
          <>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 24px', borderBottom: '1px solid var(--color-border)',
              background: 'var(--color-bg-card)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <FileCode style={{ width: '16px', height: '16px', color: 'var(--color-accent)' }} />
                <span style={{ fontSize: '14px', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>
                  {selectedActivity.file_path}
                </span>
              </div>
              <button 
                onClick={() => navigator.clipboard.writeText(selectedActivity.code_patch || selectedActivity.root_cause)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  padding: '8px 16px', borderRadius: '8px', fontSize: '12px', fontWeight: 600,
                  background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
                  color: 'var(--color-text-primary)', cursor: 'pointer',
                }}>
                <Copy style={{ width: '14px', height: '14px' }} /> Copy Result
              </button>
            </div>

            <div style={{
              margin: '24px', padding: '20px', borderRadius: '12px',
              background: 'rgba(245,158,11,0.05)', border: '1px solid rgba(245,158,11,0.15)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <AlertTriangle style={{ width: '16px', height: '16px', color: '#f59e0b' }} />
                <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>Root Cause Identification</span>
              </div>
              <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--color-text-secondary)' }}>
                {selectedActivity.root_cause}
              </p>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 24px' }}>
               <h4 style={{ color: 'var(--color-text-primary)', marginBottom: '12px', fontSize: '14px', fontWeight: 600 }}>Suggested Fix / Patch</h4>
               <pre style={{ 
                 fontFamily: 'var(--font-mono)', fontSize: '13px', lineHeight: '1.6', 
                 whiteSpace: 'pre-wrap', color: '#10b981', background: '#0d0d0f', padding: '20px', borderRadius: '12px', border: '1px solid var(--color-border)'
               }}>
                 {selectedActivity.code_patch || "No code patch provided for this activity."}
               </pre>
               {selectedActivity.explanation && (
                 <>
                   <h4 style={{ color: 'var(--color-text-primary)', margin: '24px 0 12px', fontSize: '14px', fontWeight: 600 }}>Detailed Explanation</h4>
                   <p style={{ fontSize: '14px', lineHeight: '1.7', color: 'var(--color-text-secondary)' }}>{selectedActivity.explanation}</p>
                 </>
               )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)' }}>
            Select an activity from the left to view full analysis details.
          </div>
        )}
      </div>
    </div>
  )
}
