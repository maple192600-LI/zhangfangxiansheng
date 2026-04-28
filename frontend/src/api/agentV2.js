/** Agent V2 API — SSE 聊天封装（用 XHR 保证兼容性） */
const BASE_URL = '/api/agent_v2'

/**
 * 发送消息并通过 SSE 接收流式回复
 * 使用 XMLHttpRequest 代替 fetch，避免 ReadableStream 兼容问题
 */
export function sendMessageStream(sessionId, content, { onText, onToolStart, onToolEnd, onDone, onError }) {
  const token = localStorage.getItem('zf_token')
  const xhr = new XMLHttpRequest()

  let lastLen = 0

  xhr.open('POST', `${BASE_URL}/sessions/${sessionId}/messages`, true)
  xhr.setRequestHeader('Content-Type', 'application/json')
  xhr.setRequestHeader('Authorization', `Bearer ${token}`)
  xhr.responseType = 'text'

  // 流式读取
  xhr.onprogress = function () {
    const newText = xhr.responseText.substring(lastLen)
    lastLen = xhr.responseText.length
    if (!newText) return

    // 解析 SSE 事件块（以 \n\n 分隔）
    const blocks = newText.split('\n\n')
    for (const block of blocks) {
      if (!block.trim()) continue
      let eventType = ''
      let eventData = ''
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          eventData = line.slice(6)
        }
      }
      if (!eventType || !eventData) continue

      try {
        const data = JSON.parse(eventData)
        switch (eventType) {
          case 'text': onText?.(data.text || ''); break
          case 'tool_start': onToolStart?.(data); break
          case 'tool_end': onToolEnd?.(data); break
          case 'done': onDone?.(data); break
          case 'error': onError?.(data.message || '未知错误'); break
        }
      } catch {}
    }
  }

  xhr.onload = function () {
    if (xhr.status >= 400) {
      let msg = '请求失败'
      try {
        const err = JSON.parse(xhr.responseText)
        msg = err.message || msg
      } catch {}
      onError?.(msg)
    }
    // 最终再解析一次剩余数据
    const remaining = xhr.responseText.substring(lastLen)
    if (remaining.trim()) {
      const blocks = remaining.split('\n\n')
      for (const block of blocks) {
        if (!block.trim()) continue
        let eventType = ''
        let eventData = ''
        for (const line of block.split('\n')) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim()
          else if (line.startsWith('data: ')) eventData = line.slice(6)
        }
        if (!eventType || !eventData) continue
        try {
          const data = JSON.parse(eventData)
          switch (eventType) {
            case 'done': onDone?.(data); break
            case 'error': onError?.(data.message || '未知错误'); break
          }
        } catch {}
      }
    }
    // 如果没有收到 done，也触发
    onDone?.({ stop_reason: 'xhr_end' })
  }

  xhr.onerror = function () {
    onError?.('网络错误，请检查连接')
  }

  xhr.send(JSON.stringify({ content }))

  // 返回 abort 函数
  return { abort: () => xhr.abort() }
}
