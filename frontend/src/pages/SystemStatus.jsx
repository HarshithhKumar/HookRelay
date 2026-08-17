import React, {useEffect, useState} from 'react'
import { getHealth } from '../api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export default function SystemStatus(){
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [lastChecked, setLastChecked] = useState(null)

  const check = async () => {
    setLoading(true)
    try {
      const json = await getHealth()
      setLastChecked(new Date())
      setStatus({ok: true, payload: json})
    } catch (err) {
      setLastChecked(new Date())
      setStatus({ok: false, error: err.body || err.message || String(err)})
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { check() }, [])

  return (
    <div>
      {/* Header */}
      <div style={{marginBottom: 'var(--space-2xl)'}}>
        <h1 style={{margin: 0, fontSize: '2rem', fontWeight: '600', letterSpacing: '-0.8px'}}>System Status</h1>
        <p style={{margin: 'var(--space-sm) 0 0', color: 'var(--text-muted)', fontSize: '1rem'}}>
          Monitor the health and availability of your LinkPlease automation service.
        </p>
      </div>

      {/* Status Hero Section */}
      <div className="card" style={{marginBottom: 'var(--space-2xl)'}}>
        {loading && (
          <div style={{textAlign: 'center', padding: 'var(--space-2xl)'}}>
            <div className="loading">Checking system status...</div>
          </div>
        )}

        {!loading && status && (
          <>
            {/* Main Status Display */}
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2xl)', alignItems: 'center', marginBottom: 'var(--space-2xl)', paddingBottom: 'var(--space-2xl)', borderBottom: '1px solid var(--border-subtle)'}}>
              {/* Left: Status Indicator */}
              <div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-md)',
                  marginBottom: 'var(--space-lg)'
                }}>
                  <div style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '50%',
                    background: status.ok ? 'var(--accent)' : 'var(--danger)',
                    boxShadow: status.ok ? '0 0 16px rgba(184,255,65,0.5)' : '0 0 16px rgba(255,123,123,0.5)',
                    animation: status.ok ? 'pulse 2s ease-in-out infinite' : 'none',
                    flexShrink: 0
                  }} />
                  <div>
                    <div style={{fontWeight: '500', fontSize: '1rem', color: status.ok ? 'var(--text-muted)' : 'var(--text-muted)'}}>
                      {status.ok ? 'All Systems Operational' : 'Service Unavailable'}
                    </div>
                    <div style={{fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: '4px'}}>
                      {status.ok 
                        ? 'Your LinkPlease automation service is healthy and responding normally.'
                        : 'The backend is currently unreachable. Check the service before sending new automation traffic.'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Right: Status Badge */}
              <div style={{textAlign: 'right'}}>
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 'var(--space-md)',
                  padding: 'var(--space-lg) var(--space-xl)',
                  background: status.ok ? 'rgba(184,255,65,0.08)' : 'rgba(255,123,123,0.08)',
                  border: status.ok ? '1px solid rgba(184,255,65,0.2)' : '1px solid rgba(255,123,123,0.2)',
                  borderRadius: 'var(--radius-lg)',
                  boxShadow: status.ok ? '0 0 24px rgba(184,255,65,0.15)' : 'none'
                }}>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: status.ok ? 'var(--accent)' : 'var(--danger)',
                    boxShadow: status.ok ? '0 0 12px var(--accent)' : '0 0 12px var(--danger)'
                  }} />
                  <span style={{fontSize: '0.95rem', fontWeight: '500', color: status.ok ? 'var(--accent)' : 'var(--danger)'}}>
                    {status.ok ? 'Operational' : 'Unavailable'}
                  </span>
                </div>
              </div>
            </div>

            {/* Health Details Grid */}
            {status.ok && (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 'var(--space-md)',
                marginBottom: 'var(--space-2xl)'
              }}>
                <div style={{
                  padding: 'var(--space-lg)',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(184,255,65,0.04)',
                  border: '1px solid rgba(184,255,65,0.1)'
                }}>
                  <div style={{color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '8px', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px'}}>Service</div>
                  <div style={{color: 'var(--text-primary)', fontWeight: '500', fontSize: '0.95rem'}}>LinkPlease Automation</div>
                </div>

                <div style={{
                  padding: 'var(--space-lg)',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(184,255,65,0.04)',
                  border: '1px solid rgba(184,255,65,0.1)'
                }}>
                  <div style={{color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '8px', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px'}}>API Status</div>
                  <div style={{color: 'var(--accent)', fontWeight: '500', fontSize: '0.95rem'}}>Operational</div>
                </div>

                <div style={{
                  padding: 'var(--space-lg)',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(184,255,65,0.04)',
                  border: '1px solid rgba(184,255,65,0.1)'
                }}>
                  <div style={{color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '8px', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px'}}>Health Check</div>
                  <div style={{color: 'var(--accent)', fontWeight: '500', fontSize: '0.95rem'}}>Passed</div>
                </div>
              </div>
            )}

            {/* Backend Connection Card */}
            <div style={{
              padding: 'var(--space-lg)',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid var(--border-subtle)',
              marginBottom: 'var(--space-2xl)'
            }}>
              <div style={{color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '8px', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px'}}>Backend Connection</div>
              <div style={{fontFamily: 'monospace', fontSize: '0.9rem', color: 'var(--text-secondary)', wordBreak: 'break-all'}}>{API_BASE}</div>
            </div>

            {/* Last Checked and Refresh */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingBottom: 'var(--space-lg)',
              borderBottom: '1px solid var(--border-subtle)',
              marginBottom: 'var(--space-2xl)'
            }}>
              <div style={{fontSize: '0.85rem', color: 'var(--text-subtle)'}}>
                Last checked: {lastChecked ? lastChecked.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Never'}
              </div>
              <button
                className="button primary"
                onClick={check}
                disabled={loading}
                style={{fontSize: '0.9rem'}}
              >
                ↻ Refresh status
              </button>
            </div>
          </>
        )}
      </div>

      {/* How Monitoring Works Section */}
      <div className="card" style={{marginBottom: 'var(--space-2xl)'}}>
        <h2 style={{margin: '0 0 var(--space-md) 0', fontSize: '1.125rem', fontWeight: '500', letterSpacing: '0.2px'}}>How monitoring works</h2>
        <p style={{color: 'var(--text-muted)', lineHeight: '1.6', margin: '0 0 var(--space-lg) 0'}}>
          LinkPlease checks the backend health endpoint directly to confirm that the automation service is reachable and responding. This gives you a quick view of whether the API is ready to receive comments, process automation rules, and handle background delivery work.
        </p>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 'var(--space-lg)',
          marginTop: 'var(--space-lg)'
        }}>
          <div style={{
            padding: 'var(--space-lg)',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid var(--border-subtle)'
          }}>
            <div style={{
              fontSize: '2rem',
              marginBottom: 'var(--space-md)',
              fontWeight: '600',
              color: 'var(--accent)'
            }}>01</div>
            <div style={{fontWeight: '500', fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '6px'}}>API Reachability</div>
            <div style={{fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: '1.5'}}>Confirms the backend can be reached.</div>
          </div>

          <div style={{
            padding: 'var(--space-lg)',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid var(--border-subtle)'
          }}>
            <div style={{
              fontSize: '2rem',
              marginBottom: 'var(--space-md)',
              fontWeight: '600',
              color: 'var(--accent)'
            }}>02</div>
            <div style={{fontWeight: '500', fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '6px'}}>Service Health</div>
            <div style={{fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: '1.5'}}>Confirms the automation API is responding normally.</div>
          </div>

          <div style={{
            padding: 'var(--space-lg)',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid var(--border-subtle)'
          }}>
            <div style={{
              fontSize: '2rem',
              marginBottom: 'var(--space-md)',
              fontWeight: '600',
              color: 'var(--accent)'
            }}>03</div>
            <div style={{fontWeight: '500', fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '6px'}}>Processing Readiness</div>
            <div style={{fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: '1.5'}}>Shows whether the service is available for incoming automation work.</div>
          </div>
        </div>
      </div>

      {/* What This Means Section */}
      <div className="card">
        <h2 style={{margin: '0 0 var(--space-md) 0', fontSize: '1.125rem', fontWeight: '500', letterSpacing: '0.2px'}}>What this means</h2>
        {status && status.ok ? (
          <div style={{
            padding: 'var(--space-lg)',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(184,255,65,0.04)',
            border: '1px solid rgba(184,255,65,0.1)'
          }}>
            <div style={{color: 'var(--text-primary)', fontSize: '0.95rem', lineHeight: '1.6'}}>
              Your API is reachable and ready to process requests. You can create automation rules, send comments, and the background workers can process delivery jobs without interruption.
            </div>
          </div>
        ) : status && !status.ok ? (
          <div style={{
            padding: 'var(--space-lg)',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(255,123,123,0.04)',
            border: '1px solid rgba(255,123,123,0.1)'
          }}>
            <div style={{color: 'var(--text-primary)', fontSize: '0.95rem', lineHeight: '1.6'}}>
              The backend is currently unreachable. Check the service before sending new automation traffic. Existing queued jobs will resume once the service is available.
            </div>
          </div>
        ) : (
          <div style={{color: 'var(--text-muted)', fontSize: '0.95rem'}}>Loading...</div>
        )}
      </div>
    </div>
  )
}
