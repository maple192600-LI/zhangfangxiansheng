import http from './index'

export const getPendingEvents = (params) =>
  http.get('/events/pending', { params })

export const resolveEvent = (id, data) =>
  http.put(`/events/${id}/resolve`, data)

export const voidEvent = (id, data) =>
  http.put(`/events/${id}/void`, data)
