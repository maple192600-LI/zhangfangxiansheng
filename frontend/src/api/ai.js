/**
 * AI 配置 + Agent 配置 API
 */
import http from './index'

// ── AI 配置 ──
export const getAIConfigs = () => http.get('/ai-configs')
export const createAIConfig = (data) => http.post('/ai-configs', data)
export const updateAIConfig = (id, data) => http.put(`/ai-configs/${id}`, data)
export const deleteAIConfig = (id) => http.delete(`/ai-configs/${id}`)
export const testAIConnection = (id) => http.post(`/ai-configs/${id}/test`)
export const getAICallLogs = (params) => http.get('/ai-call-logs', { params })

// ── 提供商信息 ──
export const getProviders = () => http.get('/ai-providers')
export const getApiProtocols = () => http.get('/api-protocols')
export const detectOllamaModels = () => http.get('/ai-providers/ollama/models')
export const fetchRemoteModels = (data) => http.post('/ai-configs/fetch-models', data)

// ── Agent 工作空间 ──
export const getAgentWorkspaces = () => http.get('/agent-workspaces')
