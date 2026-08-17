import React from 'react'
import { Link, useLocation } from 'react-router-dom'

const Nav = () => {
  const loc = useLocation()
  const isActive = (path) => loc.pathname === path
  return (
    <header className="header">
      <div className="container">
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <div className="brand">LinkPLEASE</div>
          <div className="small muted">Instagram comment-to-DM automation</div>
        </div>

        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <nav className="nav">
            <Link className={isActive('/') ? 'active' : ''} to="/">Dashboard</Link>
            <Link className={isActive('/rules') ? 'active' : ''} to="/rules">Rules</Link>
            <Link className={isActive('/status') ? 'active' : ''} to="/status">System Status</Link>
          </nav>

          <div className="status-pill" title="System status">
            <div className="status-dot" />
            <div className="small">System Operational</div>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Nav
