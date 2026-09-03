import { useEffect, useState } from 'react'
import { api } from '../api.js'

const FIELDS = [
  ['SLACK_WEBHOOK_URL', 'Slack incoming webhook URL', 'https://hooks.slack.com/services/...'],
  ['TWILIO_ACCOUNT_SID', 'Twilio Account SID (WhatsApp)', 'ACxxxxxxxxxxxxxxxx'],
  ['TWILIO_AUTH_TOKEN', 'Twilio Auth Token (WhatsApp)', ''],
  ['TWILIO_WHATSAPP_FROM', "Twilio WhatsApp sandbox 'from' number", 'whatsapp:+14155238886'],
  ['EMAIL_SMTP_USER', 'Email address (SMTP)', 'you@gmail.com'],
  ['EMAIL_SMTP_PASSWORD', 'SMTP app password', ''],
  ['EMAIL_SMTP_HOST', 'SMTP host (optional, default smtp.gmail.com)', 'smtp.gmail.com'],
  ['GOOGLE_SERVICE_ACCOUNT_JSON', 'Google service account JSON (paste full file contents)', '{...}'],
]

export default function Credentials() {
  const [keys, setKeys] = useState([])
  const [selectedKey, setSelectedKey] = useState(FIELDS[0][0])
  const [value, setValue] = useState('')

  async function refresh() {
    const res = await api.getCredentialKeys()
    setKeys(res.keys || [])
  }

  useEffect(() => { refresh() }, [])

  async function handleSave() {
    await api.saveCredential({ key: selectedKey, value })
    setValue('')
    refresh()
  }

  async function handleDelete(key) {
    await api.deleteCredential(key)
    refresh()
  }

  const activeField = FIELDS.find((f) => f[0] === selectedKey)

  return (
    <div>
      <h1>Credentials</h1>
      <p className="subtitle">
        Paste real API keys/webhook URLs instead of editing connector source files.
        Values are encrypted at rest and only decrypted in-memory when a connector needs them.
      </p>

      {keys.length > 0 ? (
        <div className="panel">
          <h2>Currently configured</h2>
          {keys.map((k) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0' }}>
              <span className="badge success">{k}</span>
              <button className="secondary danger" onClick={() => handleDelete(k)}>Delete</button>
            </div>
          ))}
        </div>
      ) : (
        <div className="panel empty-state">
          No credentials configured yet — every connector will run in simulated mode.
        </div>
      )}

      <div className="panel">
        <h2>Add / update a credential</h2>
        <label>Credential</label>
        <select value={selectedKey} onChange={(e) => setSelectedKey(e.target.value)}>
          {FIELDS.map(([key, display]) => (
            <option key={key} value={key}>{display}</option>
          ))}
        </select>
        <label>Value</label>
        <textarea
          rows={selectedKey === 'GOOGLE_SERVICE_ACCOUNT_JSON' ? 6 : 2}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={activeField?.[2]}
        />
        <button className="primary" onClick={handleSave}>Save credential</button>
      </div>
    </div>
  )
}
