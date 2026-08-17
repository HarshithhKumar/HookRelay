import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getHealth } from '../api'

export default function Footer() {
  const currentYear = new Date().getFullYear()
  const [healthOk, setHealthOk] = useState(false)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await getHealth()
        setHealthOk(true)
      } catch {
        setHealthOk(false)
      }
    }
    checkHealth()
  }, [])

  return (
    <footer className="footer">
      <div className="footer-content">
        <div className="footer-section">
          <h4>LinkPlease</h4>
          <p>Instagram comment-to-DM automation for creators.</p>
        </div>

        <div className="footer-section">
          <h4>Product</h4>
          <div className="footer-links">
            <Link to="/" className="footer-link">Dashboard</Link>
            <Link to="/rules" className="footer-link">Automation Rules</Link>
            <Link to="/status" className="footer-link">System Status</Link>
          </div>
        </div>

        <div className="footer-section">
          <h4>System</h4>
          <div style={{display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px'}}>
            <div className="status-dot" style={{width: '8px', height: '8px'}}></div>
            <span style={{fontSize: '0.9rem', color: 'var(--text-muted)'}}>
              {healthOk ? 'System Operational' : 'Service Unavailable'}
            </span>
          </div>
          <div style={{fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: '1.6'}}>
            API Health<br/>
            Automation Ready
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <span>© {currentYear} LinkPlease. Automation infrastructure for creator workflows.</span>
      </div>
    </footer>
  )
}
