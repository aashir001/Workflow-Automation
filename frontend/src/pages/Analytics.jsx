import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Analytics() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getAnalyticsSummary().then(setStats).catch(() => setError('Backend not reachable.'))
  }, [])

  if (error) return <div className="panel empty-state">{error}</div>
  if (!stats) return <p className="subtitle">Loading…</p>

  return (
    <div>
      <h1>Analytics</h1>
      <p className="subtitle">
        Real aggregate metrics computed directly from execution logs — not simulated numbers.
      </p>

      <div className="stat-row">
        <div className="stat">
          <div className="value">{stats.total_runs}</div>
          <div className="label">Total runs</div>
        </div>
        <div className="stat">
          <div className="value">{stats.runs_with_error}</div>
          <div className="label">Runs with an error</div>
        </div>
        <div className="stat">
          <div className="value">{stats.failure_rate_pct}%</div>
          <div className="label">Failure rate</div>
        </div>
        <div className="stat">
          <div className="value">{stats.avg_steps_per_run}</div>
          <div className="label">Avg steps / run</div>
        </div>
      </div>

      <div className="panel">
        <h2>Most-triggered workflows</h2>
        {stats.most_triggered_workflows.length === 0 ? (
          <div className="empty-state">No runs yet.</div>
        ) : (
          <table>
            <thead><tr><th>Workflow</th><th>Runs</th></tr></thead>
            <tbody>
              {stats.most_triggered_workflows.map((w, i) => (
                <tr key={i}><td>{w.workflow}</td><td>{w.runs}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h2>Failures by connector</h2>
        {stats.failures_by_connector.length === 0 ? (
          <div className="empty-state">No connector failures recorded yet.</div>
        ) : (
          <table>
            <thead><tr><th>Connector</th><th>Failures</th></tr></thead>
            <tbody>
              {stats.failures_by_connector.map((f, i) => (
                <tr key={i}><td>{f.connector}</td><td>{f.failures}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
