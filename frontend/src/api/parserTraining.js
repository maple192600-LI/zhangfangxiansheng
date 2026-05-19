import http from './index'

export const createTrainingJob = (formData) =>
  http.post('/parser-training/jobs', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })

export const getJob = (jobCode) =>
  http.get(`/parser-training/jobs/${jobCode}`)

export const runCandidate = (jobCode) =>
  http.post(`/parser-training/jobs/${jobCode}/run-candidate`)

export const saveParser = (jobCode, data) =>
  http.post(`/parser-training/jobs/${jobCode}/save-parser`, data)

export const listActiveAgents = () =>
  http.get('/parser-training/agents')

export const createAgentSession = (jobCode, data) =>
  http.post(`/parser-training/jobs/${jobCode}/agent-session`, data)

export const getParserContext = () =>
  http.get('/parser-training/context')

export const listParsers = (params) =>
  http.get('/parser-training/parsers', { params })

export const getParserDetail = (id) =>
  http.get(`/parser-training/parsers/${id}`)

export const activateParser = (id) =>
  http.post(`/parser-training/parsers/${id}/activate`)

export const retireParser = (id) =>
  http.post(`/parser-training/parsers/${id}/retire`)

export const deleteParser = (id) =>
  http.delete(`/parser-training/parsers/${id}`)
