import http from './index'

export const listWorkflows = (params) =>
  http.get('/workflow/workflows', { params })

export const createWorkflow = (data) =>
  http.post('/workflow/workflows', data)

export const getWorkflow = (id) =>
  http.get(`/workflow/workflows/${id}`)

export const updateWorkflow = (id, data) =>
  http.put(`/workflow/workflows/${id}`, data)

export const listNodes = () =>
  http.get('/workflow/nodes')

export const patchWorkflowGraph = (id, graph, changeSummary) =>
  http.patch(`/workflow/workflows/${id}/graph`, {
    patches: [{ op: 'replace_graph', graph }],
    created_by: 'user',
    change_summary: changeSummary || 'update graph from canvas',
  })

export const validateWorkflow = (id, graph) =>
  http.post(`/workflow/workflows/${id}/validate`, { graph_json: graph })

export const activateWorkflow = (id) =>
  http.post(`/workflow/workflows/${id}/activate`)

export const archiveWorkflow = (id) =>
  http.post(`/workflow/workflows/${id}/archive`)

export const startWorkflowRun = (id, input) =>
  http.post(`/workflow/workflows/${id}/runs`, { input })

export const listVersions = (id) =>
  http.get(`/workflow/workflows/${id}/versions`)

export const listRuns = (params) =>
  http.get('/workflow/runs', { params })

export const getRun = (runId) =>
  http.get(`/workflow/runs/${runId}`)

export const resumeRun = (runId) =>
  http.post(`/workflow/runs/${runId}/resume`)
