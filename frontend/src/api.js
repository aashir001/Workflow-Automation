const API_URL = 'http://localhost:8000'

async function request(path, options = {}) {
  const resp = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text || `Request failed: ${resp.status}`)
  }
  return resp.json()
}

export const api = {
  getConnectors: () => request('/meta/connectors'),
  getOperators: () => request('/meta/operators'),

  listWorkflows: () => request('/workflows'),
  getWorkflow: (id) => request(`/workflows/${id}`),
  createWorkflow: (payload) => request('/workflows', { method: 'POST', body: JSON.stringify(payload) }),
  toggleWorkflow: (id) => request(`/workflows/${id}/toggle`, { method: 'PATCH' }),
  deleteWorkflow: (id) => request(`/workflows/${id}`, { method: 'DELETE' }),
  createFromInstruction: (payload) =>
    request('/workflows/from-instruction', { method: 'POST', body: JSON.stringify(payload) }),

  submitEvent: (payload) => request('/events', { method: 'POST', body: JSON.stringify(payload) }),
  listEvents: () => request('/events'),

  listRuns: () => request('/runs'),
  getRunSteps: (runId) => request(`/runs/${runId}/steps`),

  listCustomers: () => request('/reference/customers'),
  saveCustomer: (payload) => request('/reference/customers', { method: 'POST', body: JSON.stringify(payload) }),

  getCredentialKeys: () => request('/credentials'),
  saveCredential: (payload) => request('/credentials', { method: 'POST', body: JSON.stringify(payload) }),
  deleteCredential: (key) => request(`/credentials/${key}`, { method: 'DELETE' }),

  getAnalyticsSummary: () => request('/analytics/summary'),
}
