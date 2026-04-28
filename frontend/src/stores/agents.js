import { defineStore } from 'pinia'
import { ref } from 'vue'
import http from '@/api'

export const useAgentsStore = defineStore('agents', () => {
  const list = ref([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      list.value = await http.get('/agent_v2/agents')
    } catch (e) {
      console.error('获取 agent 列表失败:', e)
      list.value = []
    } finally {
      loading.value = false
    }
  }

  async function createAgent(data) {
    const result = await http.post('/agent_v2/agents', data)
    await fetchAll()
    return result
  }

  async function updateAgent(id, data) {
    const result = await http.put(`/agent_v2/agents/${id}`, data)
    await fetchAll()
    return result
  }

  async function deleteAgent(id) {
    await http.delete(`/agent_v2/agents/${id}`)
    await fetchAll()
  }

  async function getAgent(id) {
    return await http.get(`/agent_v2/agents/${id}`)
  }

  async function fetchAIConfigs() {
    return await http.get('/agent_v2/ai-configs')
  }

  async function createSession(agentId, title) {
    return await http.post(`/agent_v2/agents/${agentId}/sessions`, { title })
  }

  async function listSessions(agentId) {
    return await http.get(`/agent_v2/agents/${agentId}/sessions`)
  }

  async function getMessages(sessionId) {
    return await http.get(`/agent_v2/sessions/${sessionId}/messages`)
  }

  async function listFiles(agentId, subDir = 'workspace') {
    return await http.get(`/agent_v2/agents/${agentId}/files`, { params: { sub_dir: subDir } })
  }

  async function uploadFile(agentId, file, subDir = 'inbox') {
    const formData = new FormData()
    formData.append('file', file)
    return await http.post(`/agent_v2/agents/${agentId}/files/upload`, formData, {
      params: { sub_dir: subDir },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  async function listSkills(agentId) {
    return await http.get(`/agent_v2/agents/${agentId}/skills`)
  }

  async function listMemories(agentId) {
    return await http.get(`/agent_v2/agents/${agentId}/memories`)
  }

  async function saveMemory(agentId, key, content) {
    return await http.post(`/agent_v2/agents/${agentId}/memories`, { key, content })
  }

  async function deleteMemory(agentId, memoryId) {
    return await http.delete(`/agent_v2/agents/${agentId}/memories/${memoryId}`)
  }

  async function deleteSession(agentId, sessionId) {
    return await http.delete(`/agent_v2/agents/${agentId}/sessions/${sessionId}`)
  }

  return {
    list, loading,
    fetchAll, createAgent, updateAgent, deleteAgent, getAgent,
    fetchAIConfigs, createSession, listSessions, getMessages,
    listFiles, uploadFile, listSkills,
    listMemories, saveMemory, deleteMemory, deleteSession,
  }
})
