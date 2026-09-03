import { useState } from 'react'
import { api } from '../api.js'

export default function BuildFromEnglish() {
  const [instruction, setInstruction] = useState('')
  const [name, setName] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleGenerate() {
    if (!instruction.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.createFromInstruction({
        instruction,
        workflow_name: name || null,
      })
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Build from English</h1>
      <p className="subtitle">
        Describe a workflow in plain English. Uses Groq's LLM if configured, otherwise
        a deterministic keyword parser — the response tells you which one ran.
      </p>

      <div className="panel">
        <label>Instruction</label>
        <textarea
          rows={3}
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="When a new order over 1500 comes in from Mumbai, email the manager and log it"
        />
        <label>Workflow name (optional)</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Untitled" />
        <button className="primary" onClick={handleGenerate} disabled={loading}>
          {loading ? 'Generating…' : 'Generate workflow'}
        </button>
      </div>

      {error && (
        <div className="panel">
          <span className="badge error">error</span>
          <p style={{ marginTop: 8 }}>{error}</p>
        </div>
      )}

      {result && (
        <div className="panel">
          <h2>
            Created workflow #{result.id}{' '}
            <span className={`badge ${result.parse_mode === 'llm' ? 'success' : 'pending'}`}>
              {result.parse_mode === 'llm' ? 'real LLM' : 'fallback parser'}
            </span>
          </h2>
          {result.llm_error && (
            <p className="hint">LLM call was attempted but failed: {result.llm_error}</p>
          )}
          <pre>{JSON.stringify(result.parsed_spec, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
