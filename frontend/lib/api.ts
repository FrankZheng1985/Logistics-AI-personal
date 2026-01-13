/**
 * API 客户端
 */
import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Dashboard API
export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats'),
  getTeamStatus: () => api.get('/dashboard/team-status'),
  getIntentDistribution: () => api.get('/dashboard/intent-distribution'),
  getRecentActivities: (limit = 10) => api.get(`/dashboard/recent-activities?limit=${limit}`),
}

// Customers API
export const customersApi = {
  list: (params?: { page?: number; page_size?: number; intent_level?: string; search?: string }) =>
    api.get('/customers', { params }),
  getHighIntent: (limit = 10) => api.get(`/customers/high-intent?limit=${limit}`),
  get: (id: string) => api.get(`/customers/${id}`),
  create: (data: any) => api.post('/customers', data),
  update: (id: string, data: any) => api.patch(`/customers/${id}`, data),
  updateIntent: (id: string, delta: number, reason?: string) =>
    api.post(`/customers/${id}/update-intent`, null, { params: { delta, reason } }),
}

// Chat API
export const chatApi = {
  listConversations: (params?: { customer_id?: string; agent_type?: string; page?: number }) =>
    api.get('/chat/conversations', { params }),
  getCustomerHistory: (customerId: string, limit = 50) =>
    api.get(`/chat/customer/${customerId}/history?limit=${limit}`),
  sendMessage: (customerId: string, content: string, agentType = 'sales') =>
    api.post('/chat/send', null, { params: { customer_id: customerId, content, agent_type: agentType } }),
}

// Videos API
export const videosApi = {
  list: (params?: { status?: string; video_type?: string; page?: number }) =>
    api.get('/videos', { params }),
  get: (id: string) => api.get(`/videos/${id}`),
  generate: (data: { title: string; description: string; video_type?: string; keywords?: string[] }) =>
    api.post('/videos/generate', null, { params: data }),
  regenerate: (id: string) => api.post(`/videos/${id}/regenerate`),
}

// Agents API
export const agentsApi = {
  list: () => api.get('/agents'),
  get: (agentType: string) => api.get(`/agents/${agentType}`),
  updateConfig: (agentType: string, config: any) => api.post(`/agents/${agentType}/config`, config),
  resetDaily: (agentType: string) => api.post(`/agents/${agentType}/reset-daily`),
}

export default api
