const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request(path, opts={}){
  const url = API_BASE.replace(/\/$/, '') + path
  const res = await fetch(url, opts)
  if(!res.ok){
    let data
    try{ data = await res.json() }catch(_){ data = {status: res.status, text: await res.text()} }
    const err = new Error('API Error')
    err.status = res.status
    err.body = data
    throw err
  }
  return res.json()
}

export function getStats(){ return request('/stats') }
export function getRules(){ return request('/rules') }
export function createRule(payload){ return request('/rules', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}) }
export function getHealth(){ return request('/health') }
