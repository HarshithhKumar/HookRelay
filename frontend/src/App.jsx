import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Nav from './components/Nav'
import Footer from './components/Footer'
import Dashboard from './pages/Dashboard'
import Rules from './pages/Rules'
import SystemStatus from './pages/SystemStatus'

export default function App(){
  return (
    <BrowserRouter>
      <div className="app-container">
        <header className="app-header">
          <Nav />
        </header>
        <main className="app-main">
          <div className="main">
            <Routes>
              <Route path="/" element={<Dashboard/>} />
              <Route path="/rules" element={<Rules/>} />
              <Route path="/status" element={<SystemStatus/>} />
              <Route path="*" element={<Dashboard/>} />
            </Routes>
          </div>
        </main>
        <footer className="app-footer">
          <Footer />
        </footer>
      </div>
    </BrowserRouter>
  )
}
