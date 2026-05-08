import http from './index'

export const invokeFundSkill = (skillName, data) =>
  http.post(`/fund/agent/skills/${skillName}/invoke`, data)

// Parser Artifact
export const listParserArtifacts = (params) =>
  http.get('/fund/parsers', { params })

export const getParserArtifact = (id) =>
  http.get(`/fund/parsers/${id}`)

export const approveParserArtifact = (id) =>
  http.post(`/fund/parsers/${id}/approve`)

export const deleteParserArtifact = (id) =>
  http.delete(`/fund/parsers/${id}`)

export const updateParserStatus = (id, status) =>
  http.patch(`/fund/parsers/${id}/status`, { status })

// Rule Artifact
export const listRuleArtifacts = (params) =>
  http.get('/fund/rules', { params })

export const getRuleArtifact = (id) =>
  http.get(`/fund/rules/${id}`)

export const approveRuleArtifact = (id) =>
  http.post(`/fund/rules/${id}/approve`)

export const deleteRuleArtifact = (id) =>
  http.delete(`/fund/rules/${id}`)

export const updateRuleStatus = (id, status) =>
  http.patch(`/fund/rules/${id}/status`, { status })

// Template Inference
export const uploadFundTemplate = (file, kind = 'cash_journal') => {
  const form = new FormData()
  form.append('file', file)
  form.append('kind', kind)
  return http.post('/fund/templates/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export const getTemplateJob = (jobId) =>
  http.get(`/fund/templates/jobs/${jobId}`)

export const confirmTemplateJob = (jobId) =>
  http.post(`/fund/templates/jobs/${jobId}/confirm`)
