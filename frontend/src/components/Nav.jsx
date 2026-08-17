import React from 'react'
import { Link, useLocation } from 'react-router-dom'

const Nav = () => {
  const loc = useLocation()
  const isActive = (path) => loc.pathname === path

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo-section">
          <div>
            <div className="brand">LinkPLEASE</div>
            <div className="brand-tagline">Instagram comment-to-DM automation</div>
          </div>
        </div>

        <nav className="nav-links">
          <Link
            className={`nav-link ${isActive('/') ? 'active' : ''}`}
            to="/"
          >
            Dashboard
          </Link>
          <Link
            className={`nav-link ${isActive('/rules') ? 'active' : ''}`}
            to="/rules"
          >
            Automation Rules
          </Link>
          <Link
            className={`nav-link ${isActive('/status') ? 'active' : ''}`}
            to="/status"
          >
            System Status
          </Link>
        </nav>

        <div className="status-indicator">
          <div className="status-dot"></div>
          <span>System Operational</span>
        </div>
      </div>
    </header>
  )
}

export default Nav
