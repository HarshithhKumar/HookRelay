import React from 'react'

export default function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="footer">
      <div className="footer-content">
        <div className="footer-section">
          <h4>LinkPLEASE</h4>
          <p>Instagram comment-to-DM automation for creators.</p>
        </div>

        <div className="footer-section">
          <h4>Product</h4>
          <div className="footer-links">
            <a href="/" className="footer-link">Dashboard</a>
            <a href="/rules" className="footer-link">Automation Rules</a>
            <a href="/status" className="footer-link">System Status</a>
          </div>
        </div>

        <div className="footer-section">
          <h4>Status</h4>
          <div className="flex" style={{alignItems: 'center', gap: '8px'}}>
            <div className="status-dot" style={{width: '8px', height: '8px'}}></div>
            <span>System Operational</span>
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <span>© {currentYear} LinkPLEASE. Automation infrastructure for creator workflows.</span>
      </div>
    </footer>
  )
}
