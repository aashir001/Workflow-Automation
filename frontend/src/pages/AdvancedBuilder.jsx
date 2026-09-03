import { useEffect, useState } from 'react'
import { api } from '../api.js'

const EXAMPLE = {
  name: 'Example: branching high-value order alert',
  trigger_type: 'new_order',
  steps: [
    {
      step_type: 'condition',
      label: 'amount > 1000?',
      config: { logic: 'AND', rules: [{ field: 'amount', operator: '>', value: '1000' }] },
      on_success_index: 1,
      on_failure_index: 2,
    },
    {
      step_type: 'action',
      label: 'Slack alert',
      config: {
        connector: 'slack',
        action: 'post_message',
        params: { channel: '#alerts', message: 'High value order: {name}' },
      },
    },
    {
      step_type: 'action',
      label: 'Quiet log',
      config: { connector: 'log', action: 'log_event', params: { message: 'Normal order: {name}' } },
    },
  ],
}

export default function AdvancedBuilder() {
  const [connectors, setConnectors] = useState(null)
  const [json, setJson] = useState(JSON.stringify(EXAMPLE, null, 2))
  const [status, setStatus] = useState(null)

  useEffect(() => {
    api.getConnectors().then(setConnectors).catch(() => setConnectors(null))
  }, [])

  async function handleCreate() {
    setStatus(null)
    try {
      const payload = JSON.parse(json)
      const res = await api.createWorkflow(payload)
      setStatus({ ok: true, message: `Created: ${JSON.stringify(res)}` })
    } catch (e) {
      setStatus({ ok: false, message: e.message })
    }
  }

  return (
    <div>
      <h1>Advanced builder</h1>
      <p className="subtitle">
        This is exactly the JSON shape the engine executes — condition steps branch on
        success/failure, action steps chain via next_index. Index 0 is the start step.
      </p>

      {connectors && (
        <div className="panel">
          <h2>Available connectors</h2>
          <pre>{JSON.stringify(connectors, null, 2)}</pre>
        </div>
      )}

      <div className="panel">
        <h2>Workflow definition (JSON)</h2>
        <textarea rows={20} value={json} onChange={(e) => setJson(e.target.value)} />
        <button className="primary" onClick={handleCreate}>
          Create workflow from JSON
        </button>
      </div>

      {status && (
        <div className="panel">
          <span className={`badge ${status.ok ? 'success' : 'error'}`}>
            {status.ok ? 'created' : 'error'}
          </span>
          <p style={{ marginTop: 8 }}>{status.message}</p>
        </div>
      )}
    </div>
  )
}
