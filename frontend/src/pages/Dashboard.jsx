import React, {useEffect, useState} from 'react'
import { getStats } from '../api'

function MetricCard({title, value, hint, icon, color}) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <div className="metric-label">{title}</div>
      <div className="metric-value">{value ?? 0}</div>
      <div className="metric-hint">{hint}</div>
    </div>
  )
}

function PipelineStep({label, icon}) {
  return (
    <div style={{textAlign: 'center'}}>
      <div style={{
        width: '48px',
        height: '48px',
        borderRadius: '12px',
        background: 'var(--accent-bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--accent)',
        fontSize: '1.5rem',
        margin: '0 auto var(--space-md)'
      }}>
        {icon}
      </div>
      <div style={{fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: '600'}}>
        {label}
      </div>
    </div>
  )
}

export default function Dashboard(){
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchStats = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getStats()
      setStats(data)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchStats() }, [])

  return (
    <div>
      {/* Hero Section */}
      <div className="hero">
        <div className="hero-text">
          <div className="eyebrow">LinkPLEASE Automation</div>
          <h1>Turn comments into conversations.</h1>
          <p>Automatically match Instagram comments, queue DMs, and track delivery across your creator workflow.</p>
        </div>
        <div className="hero-actions">
          <button className="button secondary" onClick={fetchStats}>Refresh</button>
        </div>
      </div>

      {/* Metrics Section */}
      {loading && (
        <div className="card" style={{textAlign: 'center', padding: 'var(--space-2xl)'}}>
          <div className="loading">Loading metrics...</div>
        </div>
      )}

      {error && (
        <div className="alert error">
          <span>⚠</span>
          <div>
            <div style={{fontWeight: '600', marginBottom: '4px'}}>Failed to load stats</div>
            <div>{error.message || 'Please try again'}</div>
          </div>
        </div>
      )}

      {!loading && !error && stats && (
        <>
          <div className="metrics-grid">
            <MetricCard
              title="Sent"
              value={stats.sent}
              hint="Confirmed delivered DMs"
              icon="✓"
              color="success"
            />
            <MetricCard
              title="Failed"
              value={stats.failed}
              hint="DMs that exhausted retries"
              icon="⚠"
              color="danger"
            />
            <MetricCard
              title="Queued"
              value={stats.queued}
              hint="Waiting to be processed"
              icon="⏳"
              color="accent"
            />
            <MetricCard
              title="Duplicates Blocked"
              value={stats.duplicates_blocked}
              hint="Duplicate DM attempts prevented"
              icon="✖"
              color="info"
            />
          </div>

          {/* Pipeline Visualization */}
          <div className="card" style={{marginTop: 'var(--space-2xl)'}}>
            <div className="card-header">Automation Pipeline</div>
            <div className="card-description" style={{marginBottom: 'var(--space-xl)'}}>
              How your comments become conversations
            </div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: 'var(--space-lg)',
              alignItems: 'center',
              position: 'relative'
            }}>
              <PipelineStep label="Comment Received" icon="💬" />
              <div style={{
                position: 'relative',
                height: '2px',
                background: 'var(--border-subtle)',
                margin: '0 calc(var(--space-lg) / -2)'
              }} />
              <PipelineStep label="Keyword Matched" icon="🔍" />
              <div style={{
                position: 'relative',
                height: '2px',
                background: 'var(--border-subtle)',
                margin: '0 calc(var(--space-lg) / -2)'
              }} />
              <PipelineStep label="DM Sent" icon="📬" />
              <div style={{
                position: 'relative',
                height: '2px',
                background: 'var(--border-subtle)',
                margin: '0 calc(var(--space-lg) / -2)'
              }} />
              <PipelineStep label="Delivery Reconciled" icon="✅" />
            </div>
          </div>

          {/* How It Works Grid */}
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 'var(--space-lg)', marginTop: 'var(--space-2xl)'}}>
            {/* How It Works */}
            <div className="card">
              <div className="card-header">How LinkPLEASE Works</div>
              <div style={{marginTop: 'var(--space-lg)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)'}}>
                {[
                  {num: '01', title: 'Create keyword rule', desc: 'Define automation rules with keywords'},
                  {num: '02', title: 'Receive comments', desc: 'Monitor Instagram comments'},
                  {num: '03', title: 'Match keywords', desc: 'Automatic case-insensitive matching'},
                  {num: '04', title: 'Queue DM', desc: 'Generate durable DM jobs'},
                  {num: '05', title: 'Retry safely', desc: 'Exponential backoff with stability'},
                  {num: '06', title: 'Reconcile delivery', desc: 'Confirm successful delivery'}
                ].map((step, idx) => (
                  <div key={idx} style={{display: 'flex', gap: 'var(--space-md)'}}>
                    <div style={{
                      minWidth: '40px',
                      height: '40px',
                      borderRadius: '8px',
                      background: 'var(--accent-bg)',
                      color: 'var(--accent)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: '700',
                      fontSize: '0.85rem'
                    }}>
                      {step.num}
                    </div>
                    <div style={{flex: 1}}>
                      <div style={{fontWeight: '600', color: 'var(--text-primary)'}}>
                        {step.title}
                      </div>
                      <div style={{fontSize: '0.9rem', color: 'var(--text-muted)'}}>
                        {step.desc}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Built for Unreliable APIs */}
            <div className="card">
              <div className="card-header">Built for Unreliable APIs</div>
              <div style={{marginTop: 'var(--space-lg)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)'}}>
                {[
                  {icon: '🔄', title: 'Duplicate Events', desc: 'Handles repeated event IDs gracefully'},
                  {icon: '🛡️', title: 'Failed Requests', desc: 'Durable retry with exponential backoff'},
                  {icon: '⏱️', title: 'Rate Limiting', desc: '10 requests per rolling 60 seconds'},
                  {icon: '🔒', title: 'Delivery Reconciliation', desc: 'Polls for final delivery status'},
                  {icon: '💾', title: 'Durable State', desc: 'Survives process restarts'},
                  {icon: '🔐', title: 'Idempotency Keys', desc: 'Stable keys prevent duplicates'}
                ].map((item, idx) => (
                  <div key={idx} style={{display: 'flex', gap: 'var(--space-md)', alignItems: 'flex-start'}}>
                    <div style={{fontSize: '1.5rem', marginTop: '2px'}}>
                      {item.icon}
                    </div>
                    <div style={{flex: 1}}>
                      <div style={{fontWeight: '600', color: 'var(--text-primary)'}}>
                        {item.title}
                      </div>
                      <div style={{fontSize: '0.9rem', color: 'var(--text-muted)'}}>
                        {item.desc}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {!loading && !error && !stats && (
        <div className="card" style={{textAlign: 'center', padding: 'var(--space-2xl)'}}>
          <div className="empty">
            <div className="empty-title">No data available</div>
            <div className="empty-description">Click Refresh to load current statistics</div>
          </div>
        </div>
      )}
    </div>
  )
}
