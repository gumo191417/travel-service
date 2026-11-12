const BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = await response.json()
      detail = body.detail || JSON.stringify(body)
    } catch (error) {
      // 保留状态码即可
    }
    throw new Error(detail)
  }

  if (response.status === 204) {
    return null
  }
  return response.json()
}

export const api = {
  chat({ senderId, userId, text, object }) {
    const payload = {
      sender_id: senderId,
      user_id: userId,
    }
    if (text) payload.text = text
    if (object) payload.object = object
    return request('/api/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  history(senderId) {
    const query = encodeURIComponent(senderId)
    return request(`/api/chat/history?sender_id=${query}`)
  },

  newSession(senderId, userId) {
    return request('/api/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({
        sender_id: senderId,
        user_id: userId,
      }),
    })
  },

  state(senderId) {
    const query = encodeURIComponent(senderId)
    return request(`/api/chat/state?sender_id=${query}`)
  },

  handoffList(status) {
    const suffix = status
      ? `?status=${encodeURIComponent(status)}`
      : ''
    return request(`/api/handoff/requests${suffix}`)
  },

  takeover(handoffNo, agentName) {
    return request(
      `/api/handoff/requests/${handoffNo}/takeover`,
      {
        method: 'POST',
        body: JSON.stringify({ agent_name: agentName }),
      }
    )
  },

  reply(handoffNo, text, agentName) {
    return request(
      `/api/handoff/requests/${handoffNo}/reply`,
      {
        method: 'POST',
        body: JSON.stringify({
          text,
          agent_name: agentName,
        }),
      }
    )
  },

  closeHandoff(handoffNo) {
    return request(
      `/api/handoff/requests/${handoffNo}/close`,
      { method: 'POST' }
    )
  },
}