/**
 * AI 配置 + Agent 配置 API
 */
import http from './index'

// ── AI 配置 ──
export const getAIConfigs = () => http.get('/ai-configs')
export const createAIConfig = (data) => http.post('/ai-configs', data)
export const updateAIConfig = (id, data) => http.put(`/ai-configs/${id}`, data)
export const testAIConnection = (id) => http.post(`/ai-configs/${id}/test`)

// ── Agent 配置 ──
export const getAgentConfigs = () => http.get('/agent-configs')
export const updateAgentConfig = (id, data) => http.put(`/agent-configs/${id}`, data)
