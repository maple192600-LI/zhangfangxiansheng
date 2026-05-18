import http from './index'

export const createTrainingJob = (formData) =>
  http.post('/parser-training/jobs', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })

export const runCandidate = (data) =>
  http.post('/parser-training/run-candidate', data)

export const saveParser = (data) =>
  http.post('/parser-training/save-parser', data)

export const getAgentSession = (data) =>
  http.post('/parser-training/agent-session', data)

export const getParserContext = () =>
  http.get('/parser-training/context')

export const listParsers = (params) =>
  http.get('/parser-training/parsers', { params })
