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
      setLastChecked(new Date().toISOString())
      setStatus({ok: true, payload: json})
    } catch (err) {
      setLastChecked(new Date().toISOString())
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
        <h1 style={{margin: 0, fontSize: '2rem', fontWeight: '800'}}>System Status</h1>
        <p style={{margin: 'var(--space-sm) 0 0', color: 'var(--text-muted)'}}>
          Monitor the health and availability of your LinkPLEASE automation service.
        </p>
      </div>

      {/* Status Overview Card */}
      <div className="card" style={{marginBottom: 'var(--space-2xl)'}}>
        {loading && (
          <div style={{textAlign: 'center', padding: 'var(--space-2xl)'}}>
            <div className="loading">Checking system status...</div>
          </div>
        )}

        {!loading && status && (
          <>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-md)',
              marginBottom: 'var(--space-xl)',
              paddingBottom: 'var(--space-xl)',
              borderBottom: '1px solid var(--border-subtle)'
            }}>
              <div style={{
                width: '16px',
                height: '16px',
                borderRadius: '50%',
                background: status.ok ? 'var(--success)' : 'var(--danger)',
                boxShadow: status.ok ? '0 0 12px rgba(52,211,153,0.4)' : '0 0 12px rgba(255,123,123,0.4)',
                animation: status.ok ? 'pulse 2s ease-in-out infinite' : 'none'
              }} />
              <div style={{fontWeight: '700', fontSize: '1.1rem', color: status.ok ? 'var(--success)' : 'var(--danger)'}}>
                {status.ok ? '✓ All Systems Operational' : '✕ Service Unavailable'}
              </div>
            </div>

            {status.ok && (
              <>
                <div style={{
                  background: 'rgba(52,211,153,0.06)',
                  border: '1px solid rgba(52,211,153,0.2)',
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--space-lg)',
                  marginBottom: 'var(--space-lg)'
                }}>
                  <div style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>
                    🎉 Your automation service is running smoothly. All endpoints are responding correctly.
                  </div>
                </div>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: 'var(--space-md)',
                  marginTop: 'var(--space-lg)'
                }}>
                  <div style={{padding: 'var(--space-md)', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)'}}>
                    <div style={{color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '4px'}}>API Status</div>
                    <div style={{color: 'var(--success)', fontWeight: '600'}}>Operational</div>
                  </div>
                  <div style={{padding: 'var(--space-md)', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)'}}>
                    <div style={{color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '4px'}}>Backend URL</div>
                    <div style={{fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)', wordBreak: 'break-all'}}>{API_BASE}</div>
                  </div>
                </div>

                {/* Detailed Status */}
                <div style={{marginTop: 'var(--space-xl)', paddingTop: 'var(--space-xl)', borderTop: '1px solid var(--border-subtle)'}}>
                  <div style={{fontWeight: '600', marginBottom: 'var(--space-md)'}}>Service Details</div>
                  <pre style={{
                    background: 'rgba(255,255,255,0.02)',
                    padding: 'var(--space-md)',
                    borderRadius: 'var(--radius-md)',
                    overflow: 'auto',
                    fontSize: '0.85rem',
                    color: 'var(--text-muted)',
                    fontFamily: 'monospace'
                  }}>
                    {JSON.stringify(status.payload, null, 2)}
                  </pre>
                </div>
              </>
            )}

            {!status.ok && (
              <div style={{
                background: 'rgba(255,123,123,0.06)',
                border: '1px solid rgba(255,123,123,0.2)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-lg)'
              }}>
                <div style={{color: 'var(--danger)', fontWeight: '600', marginBottom: '4px'}}>Connection Failed</div>
                <div style={{fontSize: '0.9rem', color: 'var(--text-muted)'}}>
                  Unable to reach the backend service. Please check your connection and try again.
                </div>
              </div>
            )}

            <div style={{
              marginTop: 'var(--space-xl)',
              paddingTop: 'var(--space-lg)',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div style={{fontSize: '0.85rem', color: 'var(--text-subtle)'}}>
                Last checked: {lastChecked ? new Date(lastChecked).toLocaleString() : 'Never'}
              </div>
              <button
                className="button primary"
                onClick={check}
                disabled={loading}
              >
                Refresh Status
              </button>
            </div>
          </>
        )}
      </div>

      {/* Information Card */}
      <div className="card">
        <div className="card-header">About System Monitoring</div>
        <p style={{color: 'var(--text-muted)', lineHeight: '1.6', margin: 0}}>
          LinkPLEASE uses a health check endpoint to confirm that your automation service is operational. This page connects to the backend API to verify availability and responsiveness. If the service is unavailable, no new automations can be created or processed.
        </p>
      </div>
    </div>
  )
}
