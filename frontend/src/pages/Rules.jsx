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

  const fetchRules = async () =>{
    setLoading(true); setError(null)
    try{
      const data = await getRules()
      setRules(data)
    }catch(err){
      setError(err)
    }finally{setLoading(false)}
  }

  useEffect(()=>{fetchRules()}, [])

  const submit = async (e) =>{
    e.preventDefault(); setSubmitting(true); setError(null); setSuccess(null)
    const trimmedKeyword = keyword.trim();
    const trimmedMsg = dmMessage.trim();
    if(!trimmedKeyword || !trimmedMsg){setError('Both fields are required'); setSubmitting(false); return}
    try{
      await createRule({keyword: trimmedKeyword, dm_message: trimmedMsg})
      setSuccess('Rule created')
      setKeyword(''); setDmMessage('')
      fetchRules()
    }catch(err){
      setError(err.body || err.message || String(err))
    }finally{setSubmitting(false)}
  }

  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
        <div>
          <h2 style={{fontSize:20,fontWeight:700}}>Automation Rules</h2>
          <div className="small muted">Define what should happen when someone comments on your posts.</div>
        </div>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 360px',gap:16}}>
        <div>
          <h3 style={{marginTop:0}}>Existing rules</h3>
          {loading && <div>Loading...</div>}
          {error && <div className="alert error">{typeof error === 'string' ? error : JSON.stringify(error)}</div>}
          {!loading && rules.length === 0 && <div className="empty">No automation rules yet. Create your first rule using the form.</div>}
          <div style={{marginTop:12}}>
            {rules.map(r => (
              <div key={r.rule_id} className="card" style={{marginBottom:12}}>
                <div className="label">Keyword</div>
                <div style={{fontWeight:700,fontSize:16}}>{r.keyword}</div>
                <div className="label" style={{marginTop:8}}>Message</div>
                <div style={{marginTop:6}}>{r.dm_message}</div>
                <div className="small muted" style={{marginTop:8}}>ID: {r.rule_id}</div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="card">
            <h3 style={{marginTop:0}}>Create Rule</h3>
            <form onSubmit={submit} className="form" style={{marginTop:8}}>
              {success && <div className="alert success" style={{marginBottom:8}}>{success}</div>}
              {error && <div className="alert error" style={{marginBottom:8}}>{typeof error === 'string' ? error : JSON.stringify(error)}</div>}
              <div className="row">
                <label>Keyword</label>
                <input value={keyword} onChange={e=>setKeyword(e.target.value)} required />
              </div>
              <div className="row">
                <label>DM Message</label>
                <textarea value={dmMessage} onChange={e=>setDmMessage(e.target.value)} required rows={3} />
              </div>
              <div style={{display:'flex',justifyContent:'flex-end'}}>
                <button disabled={submitting} className="button primary">Create Rule</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
