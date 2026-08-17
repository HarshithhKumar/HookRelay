import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Nav from './components/Nav'
import Dashboard from './pages/Dashboard'
import Rules from './pages/Rules'
import SystemStatus from './pages/SystemStatus'

export default function App(){
  return (
    <BrowserRouter>
      <div>
        <Nav />
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard/>} />
            <Route path="/rules" element={<Rules/>} />
            <Route path="/status" element={<SystemStatus/>} />
            <Route path="*" element={<Dashboard/>} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
