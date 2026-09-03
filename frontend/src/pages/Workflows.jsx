import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Workflows() {
  const [workflows, setWorkflows] = useState([])
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)

  async function refresh() {
    try {
      setWorkflows(await api.listWorkflows())
      setError(null)
    } catch (e) {
      setError('Backend not reachable — is uvicorn app.main:app --reload running?')
    }
  }

  useEffect(() => { refresh() }, [])

  async function handleInspect(id) {
    setDetail(await api.getWorkflow(id))
  }

  async function handleToggle(id) {
    await api.toggleWorkflow(id)
    refresh()
  }

  async function handleDelete(id) {
    await api.deleteWorkflow(id)
    if (detail?.id === id) setDetail(null)
    refresh()
  }

  return (
    <div>
      <h1>Workflows</h1>
      <p className="subtitle">Every workflow that currently exists, whether built via English, JSON, or seeded.</p>

      {error && <div className="panel empty-state">{error}</div>}

      {!error && workflows.length === 0 && (
        <div className="panel empty-state">No workflows yet — create one from another tab, or run seed_data.py.</div>
      )}

      {workflows.length > 0 && (
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>ID</th><th>Name</th><th>Trigger</th><th>Steps</th><th>Active</th><th></th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((w) => (
                <tr key={w.id}>
                  <td>{w.id}</td>
                  <td>{w.name}</td>
                  <td><span className="badge neutral">{w.trigger_type}</span></td>
                  <td>{w.step_count}</td>
                  <td>
                    <span className={`badge ${w.is_active ? 'success' : 'neutral'}`}>
                      {w.is_active ? 'active' : 'inactive'}
                    </span>
                  </td>
                  <td style={{ display: 'flex', gap: 6 }}>
                    <button className="secondary" onClick={() => handleInspect(w.id)}>Inspect</button>
                    <button className="secondary" onClick={() => handleToggle(w.id)}>Toggle</button>
                    <button className="secondary danger" onClick={() => handleDelete(w.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {detail && (
        <div className="panel">
          <h2>Workflow #{detail.id} — {detail.name}</h2>
          <pre>{JSON.stringify(detail, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
