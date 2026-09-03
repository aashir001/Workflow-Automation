import { useState } from 'react'
import BuildFromEnglish from './pages/BuildFromEnglish.jsx'
import AdvancedBuilder from './pages/AdvancedBuilder.jsx'
import Workflows from './pages/Workflows.jsx'
import SimulateEvent from './pages/SimulateEvent.jsx'
import ExecutionAudit from './pages/ExecutionAudit.jsx'
import ReferenceData from './pages/ReferenceData.jsx'
import Credentials from './pages/Credentials.jsx'
import Analytics from './pages/Analytics.jsx'

const PAGES = [
  { key: 'nl', label: 'Build from English', component: BuildFromEnglish },
  { key: 'advanced', label: 'Advanced builder', component: AdvancedBuilder },
  { key: 'workflows', label: 'Workflows', component: Workflows },
  { key: 'simulate', label: 'Simulate event', component: SimulateEvent },
  { key: 'audit', label: 'Execution audit trail', component: ExecutionAudit },
  { key: 'reference', label: 'Reference data', component: ReferenceData },
  { key: 'credentials', label: 'Credentials', component: Credentials },
  { key: 'analytics', label: 'Analytics', component: Analytics },
]

export default function App() {
  const [active, setActive] = useState('nl')
  const Page = PAGES.find((p) => p.key === active)?.component ?? BuildFromEnglish

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-title">
          <strong>Workflow Engine</strong>
          branching · connectors · audit
        </div>
        {PAGES.map((p) => (
          <button
            key={p.key}
            className={`nav-item ${active === p.key ? 'active' : ''}`}
            onClick={() => setActive(p.key)}
          >
            {p.label}
          </button>
        ))}
      </aside>
      <main className="main">
        <Page />
      </main>
    </div>
  )
}
