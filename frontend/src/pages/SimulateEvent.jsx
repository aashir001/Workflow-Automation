import { useState } from 'react'
import { api } from '../api.js'

export default function SimulateEvent() {
  const [trigger, setTrigger] = useState('new_order')
  const [dataText, setDataText] = useState(
    '{"name": "Aashir", "region": "Delhi", "amount": 1500, "customer_id": "CUST001"}'
  )
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSend() {
    setError(null)
    try {
      const data = JSON.parse(dataText)
      const res = await api.submitEvent({ trigger_type: trigger, data })
      setResult(res)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h1>Simulate event</h1>
      <p className="subtitle">
        Manual simulation path. Real external systems should instead POST to
        /webhooks/&#123;trigger_type&#125;.
      </p>

      <div className="panel">
        <label>Trigger type</label>
        <select value={trigger} onChange={(e) => setTrigger(e.target.value)}>
          <option>new_order</option>
          <option>new_signup</option>
          <option>row_added</option>
          <option>status_changed</option>
        </select>
        <label>Event data (JSON)</label>
        <textarea rows={4} value={dataText} onChange={(e) => setDataText(e.target.value)} />
        <button className="primary" onClick={handleSend}>Send event</button>
      </div>

      {error && (
        <div className="panel">
          <span className="badge error">error</span>
          <p style={{ marginTop: 8 }}>{error}</p>
        </div>
      )}

      {result && (
        <div className="panel">
          <h2>Result</h2>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
