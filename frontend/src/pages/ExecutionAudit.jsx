import { useEffect, useState } from 'react'
import { api } from '../api.js'

const STATUS_BADGE = {
  passed: 'success', success: 'success', applied: 'success',
  failed: 'neutral', skipped: 'neutral',
  error: 'error',
}

export default function ExecutionAudit() {
  const [runs, setRuns] = useState([])
  const [selectedRunId, setSelectedRunId] = useState(null)
  const [steps, setSteps] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    api.listRuns().then(setRuns).catch(() => setError('Backend not reachable.'))
  }, [])

  async function handleInspect(runId) {
    setSelectedRunId(runId)
    setSteps(await api.getRunSteps(runId))
  }

  return (
    <div>
      <h1>Execution audit trail</h1>
      <p className="subtitle">
        Every run of every workflow's graph. Pick a run to see exactly which steps it
        visited and what the working data looked like at each point.
      </p>

      {error && <div className="panel empty-state">{error}</div>}

      {!error && runs.length === 0 && (
        <div className="panel empty-state">No runs yet — simulate an event first.</div>
      )}

      {runs.length > 0 && (
        <div className="panel">
          <table>
            <thead>
              <tr><th>Run</th><th>Workflow ID</th><th>Status</th><th>Started</th><th></th></tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.workflow_id}</td>
                  <td><span className={`badge ${STATUS_BADGE[r.status] || 'neutral'}`}>{r.status}</span></td>
                  <td style={{ color: 'var(--text-dim)', fontSize: 12 }}>{r.started_at}</td>
                  <td><button className="secondary" onClick={() => handleInspect(r.id)}>Trace</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedRunId && (
        <div className="panel">
          <h2>Run #{selectedRunId} — step trace</h2>
          <div className="step-trace">
            {steps.map((s, i) => (
              <div className="step-trace-item" key={i}>
                <div className="step-head">
                  <span className={`badge ${STATUS_BADGE[s.status] || 'neutral'}`}>{s.status}</span>{' '}
                  Step {s.step_id} ({s.step_type})
                </div>
                <div style={{ fontSize: 13, marginBottom: 6 }}>{s.detail}</div>
                <details>
                  <summary style={{ cursor: 'pointer', fontSize: 12, color: 'var(--text-dim)' }}>
                    Working data
                  </summary>
                  <pre>{JSON.stringify(s.working_data, null, 2)}</pre>
                </details>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
