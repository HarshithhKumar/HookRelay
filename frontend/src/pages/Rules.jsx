import React, {useEffect, useState} from 'react'
import { getRules, createRule } from '../api'

export default function Rules(){
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [keyword, setKeyword] = useState('')
  const [dmMessage, setDmMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(null)

  const fetchRules = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getRules()
      setRules(data)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchRules() }, [])

  const submit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setSuccess(null)
    const trimmedKeyword = keyword.trim()
    const trimmedMsg = dmMessage.trim()
    if (!trimmedKeyword || !trimmedMsg) {
      setError('Both keyword and message are required')
      setSubmitting(false)
      return
    }
    try {
      await createRule({keyword: trimmedKeyword, dm_message: trimmedMsg})
      setSuccess('✓ Rule created successfully')
      setKeyword('')
      setDmMessage('')
      await fetchRules()
    } catch (err) {
      setError(err.body?.message || err.message || 'Failed to create rule')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      {/* Header */}
      <div style={{marginBottom: 'var(--space-2xl)'}}>
        <h1 style={{margin: 0, fontSize: '2rem', fontWeight: '600', letterSpacing: '-0.8px'}}>Automation Rules</h1>
        <p style={{margin: 'var(--space-sm) 0 0', color: 'var(--text-muted)', fontSize: '1rem'}}>
          Define automation rules. When someone comments with a keyword, we automatically send them a DM.
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid-2">
        {/* Existing Rules Column */}
        <div>
          <h2 style={{fontSize: '1.25rem', fontWeight: '500', marginBottom: 'var(--space-lg)', letterSpacing: '-0.3px'}}>
            {rules.length > 0 ? 'Your Rules' : 'No Rules Yet'}
          </h2>

          {loading && (
            <div className="card" style={{textAlign: 'center', padding: 'var(--space-2xl)'}}>
              <div className="loading">Loading rules...</div>
            </div>
          )}

          {!loading && error && (
            <div className="alert error">
              <span>⚠</span>
              <div>
                <div style={{fontWeight: '600'}}>Failed to load rules</div>
              </div>
            </div>
          )}

          {!loading && rules.length === 0 && !error && (
            <div className="card" style={{textAlign: 'center', padding: 'var(--space-2xl)'}}>
              <div className="empty">
                <div className="empty-title">No automation rules yet</div>
                <div className="empty-description">
                  Create your first keyword rule to start automatically responding to comments.
                </div>
              </div>
            </div>
          )}

          {!loading && rules.length > 0 && (
            <div style={{display: 'flex', flexDirection: 'column', gap: 'var(--space-md)'}}>
              {rules.map((rule) => (
                <div key={rule.rule_id} className="card">
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-md)'}}>
                    <div style={{
                      display: 'inline-block',
                      background: 'var(--accent-bg)',
                      color: 'var(--accent)',
                      padding: '4px 12px',
                      borderRadius: '20px',
                      fontSize: '0.85rem',
                      fontWeight: '600'
                    }}>
                      {rule.keyword}
                    </div>
                  </div>
                  <div style={{color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: 'var(--space-sm)'}}>
                    DM Template
                  </div>
                  <div style={{
                    background: 'rgba(255,255,255,0.02)',
                    padding: 'var(--space-md)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.95rem',
                    lineHeight: '1.6',
                    marginBottom: 'var(--space-md)',
                    borderLeft: '2px solid var(--accent)'
                  }}>
                    {rule.dm_message}
                  </div>
                  <div style={{fontSize: '0.75rem', color: 'var(--text-subtle)', fontFamily: 'monospace'}}>
                    ID: {rule.rule_id}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Create Rule Column */}
        <div>
          <div className="card" style={{height: 'fit-content'}}>
            <div className="card-header">Create New Rule</div>
            <p style={{color: 'var(--text-muted)', fontSize: '0.9rem', margin: '0 0 var(--space-lg)'}}>
              Set up a new automation rule
            </p>

            <form onSubmit={submit} className="form">
              {success && (
                <div className="alert success">
                  <span>✓</span>
                  <div>{success}</div>
                </div>
              )}
              {error && (
                <div className="alert error">
                  <span>⚠</span>
                  <div>{error}</div>
                </div>
              )}

              <div className="form-group">
                <label htmlFor="keyword" className="form-label">Keyword</label>
                <input
                  id="keyword"
                  className="form-input"
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="e.g., price, shipping, discount"
                  required
                />
                <div style={{fontSize: '0.8rem', color: 'var(--text-subtle)', marginTop: '4px'}}>
                  Trigger when comments contain this word
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="message" className="form-label">DM Message</label>
                <textarea
                  id="message"
                  className="form-textarea"
                  value={dmMessage}
                  onChange={(e) => setDmMessage(e.target.value)}
                  placeholder="Message to send automatically..."
                  required
                />
                <div style={{fontSize: '0.8rem', color: 'var(--text-subtle)', marginTop: '4px'}}>
                  Message sent to users who match the keyword
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="button primary"
                style={{width: '100%'}}
              >
                {submitting ? '⏳ Creating...' : '✓ Create Rule'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
