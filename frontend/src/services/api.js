import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Repository endpoints
export const repositoryAPI = {
  connect: (data) => api.post('/repository/connect', data),
  list: () => api.get('/repository/list'),
  getStatus: (id) => api.get(`/repository/${id}/status`),
}

// Debug / Analysis endpoints
export const debugAPI = {
  analyze: (data) => api.post('/debug/analyze', data),
}

// Search endpoints
export const searchAPI = {
  search: (data) => api.post('/search', data),
}

// Activity endpoints
export const activityAPI = {
  getAll: (params) => api.get('/activity', { params }),
  getById: (id) => api.get(`/activity/${id}`),
}

export default api
