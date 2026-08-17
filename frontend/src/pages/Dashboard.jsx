import React, {useEffect, useState} from 'react'
import { getStats } from '../api'

function Metric({title, value, hint, icon}){
  return (
    <div className="card">
      <div className="metric-row">
        <div className="metric-icon">{icon}</div>
        <div>
          <div className="label">{title}</div>
          <div className="value">{value ?? 0}</div>
          {hint && <div className="small muted">{hint}</div>}
        </div>
      </div>
    </div>
  )
}

export default function Dashboard(){
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchStats = async () => {
    setLoading(true); setError(null)
    try{
      const data = await getStats()
      setStats(data)
    }catch(err){
      setError(err)
    }finally{setLoading(false)}
  }

  useEffect(()=>{ fetchStats() }, [])

  return (
    <div>
      <div className="hero">
        <div>
          <div className="eyebrow">LINKPLEASE AUTOMATION</div>
          <h1>Turn comments into conversations.</h1>
          <p>Automatically match Instagram comments, queue DMs, and track delivery.</p>
        </div>
        <div className="hero-actions">
          <button className="button secondary" onClick={fetchStats}>Refresh</button>
          <button className="button primary" onClick={fetchStats}>Live Update</button>
        </div>
      </div>

      {loading && <div className="card">Loading...</div>}
      {error && <div className="alert error">Error: {error.message || String(error)}</div>}

      {!loading && !error && stats && (
        <div className="metrics">
          <Metric title="Sent" value={stats.sent} hint="Confirmed delivered DMs" icon="✓" />
          <Metric title="Failed" value={stats.failed} hint="DMs that exhausted retries" icon="⚠" />
          <Metric title="Queued" value={stats.queued} hint="Waiting to be processed" icon="⏳" />
          <Metric title="Duplicates Blocked" value={stats.duplicates_blocked} hint="Duplicate DM attempts prevented" icon="✖" />
        </div>
      )}

      <div className="grid-cards">
        <div className="card">
          <h3>Automation overview</h3>
          <div className="small muted" style={{marginTop:8}}>
            Comment received<br/>Keyword matched<br/>DM queued<br/>DM sent<br/>Delivery reconciled
          </div>
        </div>
        <div className="card">
          <h3>How LinkPLEASE works</h3>
          <ol className="small muted" style={{marginTop:8}}>
            <li>Create a keyword rule</li>
            <li>Receive a comment</li>
            <li>Match the keyword</li>
            <li>Queue the DM</li>
            <li>Retry safely if needed</li>
            <li>Reconcile delivery</li>
          </ol>
        </div>
      </div>

    </div>
  )
}
