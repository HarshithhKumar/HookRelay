import React, {useEffect, useState} from 'react'
import { getHealth } from '../api'

export default function SystemStatus(){
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [lastChecked, setLastChecked] = useState(null)

  const check = async ()=>{
    setLoading(true)
    try{
      const json = await getHealth()
      setLastChecked(new Date().toISOString())
      setStatus({ok:true, payload: json})
    }catch(err){
      setLastChecked(new Date().toISOString())
      setStatus({ok:false, error: err.body || err.message || String(err)})
    }finally{setLoading(false)}
  }

  useEffect(()=>{check()}, [])

  const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
        <h2 style={{fontSize:20,fontWeight:600}}>System Status</h2>
        <button onClick={check} className="button">Check</button>
      </div>
      {loading && <div className="card">Checking...</div>}
      {!loading && status && (
        <div className={`card`} style={{background: status.ok ? '#ecfdf5' : '#fff1f2'}}>
          {status.ok ? (
            <div>Backend is online: <pre style={{fontSize:12}}>{JSON.stringify(status.payload)}</pre></div>
          ) : (
            <div>Backend offline or error: <pre style={{fontSize:12}}>{JSON.stringify(status)}</pre></div>
          )}
          <div style={{marginTop:8,fontSize:12,color:'#6b7280'}}>API URL: {apiUrl}</div>
          <div style={{marginTop:4,fontSize:12,color:'#6b7280'}}>Last checked: {lastChecked}</div>
        </div>
      )}
    </div>
  )
}
