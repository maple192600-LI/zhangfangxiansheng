import http from './index'

// ParserArtifact
export const listParserArtifacts = (params) =>
  http.get('/artifacts/parsers', { params })

export const getParserArtifact = (id) =>
  http.get(`/artifacts/parsers/${id}`)

export const createParserArtifactDraft = (data) =>
  http.post('/artifacts/parsers/drafts', data)

export const approveParserArtifact = (id, data = {}) =>
  http.post(`/artifacts/parsers/${id}/approve`, data)

export const rejectParserArtifact = (id, data = {}) =>
  http.post(`/artifacts/parsers/${id}/reject`, data)

// RuleArtifact
export const listRuleArtifacts = (params) =>
  http.get('/artifacts/rules', { params })

export const getRuleArtifact = (id) =>
  http.get(`/artifacts/rules/${id}`)

export const createRuleArtifactDraft = (data) =>
  http.post('/artifacts/rules/drafts', data)

export const approveRuleArtifact = (id, data = {}) =>
  http.post(`/artifacts/rules/${id}/approve`, data)

export const rejectRuleArtifact = (id, data = {}) =>
  http.post(`/artifacts/rules/${id}/reject`, data)

// TemplateInferenceJob
export const listTemplateInferenceJobs = (params) =>
  http.get('/artifacts/template-inference-jobs', { params })

export const getTemplateInferenceJob = (id) =>
  http.get(`/artifacts/template-inference-jobs/${id}`)
