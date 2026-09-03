import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function ReferenceData() {
  const [customers, setCustomers] = useState([])
  const [form, setForm] = useState({ customer_id: '', tier: 'gold', region: '' })
  const [error, setError] = useState(null)

  async function refresh() {
    try {
      setCustomers(await api.listCustomers())
    } catch (e) {
      setError('Backend not reachable.')
    }
  }

  useEffect(() => { refresh() }, [])

  async function handleSave() {
    await api.saveCustomer(form)
    setForm({ customer_id: '', tier: 'gold', region: '' })
    refresh()
  }

  return (
    <div>
      <h1>Reference data</h1>
      <p className="subtitle">
        Backs the sql_lookup connector's get_customer_tier action — used by transform
        steps to enrich events with real data.
      </p>

      {error && <div className="panel empty-state">{error}</div>}

      {customers.length > 0 && (
        <div className="panel">
          <table>
            <thead><tr><th>Customer ID</th><th>Tier</th><th>Region</th></tr></thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.customer_id}>
                  <td>{c.customer_id}</td>
                  <td><span className="badge neutral">{c.tier}</span></td>
                  <td>{c.region}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="panel">
        <h2>Add / update a customer</h2>
        <div className="grid-3">
          <div>
            <label>Customer ID</label>
            <input
              value={form.customer_id}
              onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
              placeholder="CUST004"
            />
          </div>
          <div>
            <label>Tier</label>
            <select value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })}>
              <option>gold</option><option>silver</option><option>bronze</option>
            </select>
          </div>
          <div>
            <label>Region</label>
            <input
              value={form.region}
              onChange={(e) => setForm({ ...form, region: e.target.value })}
              placeholder="Hyderabad"
            />
          </div>
        </div>
        <button className="primary" onClick={handleSave}>Save</button>
      </div>
    </div>
  )
}
