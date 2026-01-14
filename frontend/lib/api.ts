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

// Leads API - 线索管理
export const leadsApi = {
  list: (params?: { 
    page?: number
    page_size?: number
    status?: string
    intent_level?: string
    source?: string
    search?: string 
  }) => api.get('/leads', { params }),
  get: (id: string) => api.get(`/leads/${id}`),
  create: (data: {
    name?: string
    company?: string
    phone?: string
    email?: string
    wechat?: string
    source?: string
    source_url?: string
    needs?: string[]
    tags?: string[]
  }) => api.post('/leads', data),
  update: (id: string, data: any) => api.patch(`/leads/${id}`, data),
  delete: (id: string) => api.delete(`/leads/${id}`),
  convert: (id: string) => api.post(`/leads/${id}/convert`),
  markInvalid: (id: string, reason?: string) => 
    api.post(`/leads/${id}/invalid`, null, { params: { reason } }),
  getStats: () => api.get('/leads/stats'),
  searchOnline: (keyword: string) => 
    api.post('/leads/search-online', null, { params: { keyword } }),
}

// Follow API - 跟进管理
export const followApi = {
  list: (params?: {
    page?: number
    page_size?: number
    customer_id?: string
    follow_type?: string
    result?: string
    date_from?: string
    date_to?: string
  }) => api.get('/follow/records', { params }),
  get: (id: string) => api.get(`/follow/records/${id}`),
  create: (data: {
    customer_id: string
    follow_type: string
    content: string
    result?: string
    next_follow_at?: string
  }) => api.post('/follow/records', data),
  update: (id: string, data: any) => api.patch(`/follow/records/${id}`, data),
  getTodayTasks: () => api.get('/follow/today-tasks'),
  getCustomerSummary: (customerId: string) => api.get(`/follow/customer/${customerId}/summary`),
  scheduleFollowUp: (customerId: string, followAt: string, content?: string) =>
    api.post(`/follow/schedule`, null, { params: { customer_id: customerId, follow_at: followAt, content } }),
}

// Knowledge API - 知识库管理
export const knowledgeApi = {
  list: (params?: {
    page?: number
    page_size?: number
    category?: string
    search?: string
  }) => api.get('/knowledge', { params }),
  get: (id: string) => api.get(`/knowledge/${id}`),
  create: (data: {
    title: string
    content: string
    category?: string
    tags?: string[]
    source?: string
  }) => api.post('/knowledge', data),
  update: (id: string, data: any) => api.patch(`/knowledge/${id}`, data),
  delete: (id: string) => api.delete(`/knowledge/${id}`),
  search: (query: string, limit?: number) =>
    api.get('/knowledge/search', { params: { query, limit } }),
  getCategories: () => api.get('/knowledge/categories'),
  getStats: () => api.get('/knowledge/stats'),
}

// Reports API - 报表管理
export const reportsApi = {
  getDaily: (date?: string) => api.get('/reports/daily', { params: { date } }),
  getWeekly: (weekStart?: string) => api.get('/reports/weekly', { params: { week_start: weekStart } }),
  getMonthly: (month?: string) => api.get('/reports/monthly', { params: { month } }),
  getCustomerAnalysis: (params?: { 
    date_from?: string
    date_to?: string
    group_by?: string 
  }) => api.get('/reports/customer-analysis', { params }),
  getConversionFunnel: (params?: { 
    date_from?: string
    date_to?: string 
  }) => api.get('/reports/conversion-funnel', { params }),
  getAgentPerformance: (params?: { 
    date_from?: string
    date_to?: string
    agent_type?: string 
  }) => api.get('/reports/agent-performance', { params }),
  exportReport: (reportType: string, format: 'csv' | 'excel' | 'pdf', params?: any) =>
    api.get(`/reports/export/${reportType}`, { 
      params: { format, ...params },
      responseType: 'blob'
    }),
}

// Monitoring API - 系统监控
export const monitoringApi = {
  getHealth: () => api.get('/monitoring/health'),
  getSystemStats: () => api.get('/monitoring/system-stats'),
  getAgentLogs: (params?: {
    agent_type?: string
    level?: string
    date_from?: string
    date_to?: string
    page?: number
    page_size?: number
  }) => api.get('/monitoring/agent-logs', { params }),
  getApiStatus: () => api.get('/monitoring/api-status'),
  getQueueStats: () => api.get('/monitoring/queue-stats'),
  getErrorLogs: (params?: {
    date_from?: string
    date_to?: string
    page?: number
    page_size?: number
  }) => api.get('/monitoring/error-logs', { params }),
  triggerHealthCheck: () => api.post('/monitoring/trigger-health-check'),
  getAlerts: (params?: { 
    status?: string
    severity?: string 
  }) => api.get('/monitoring/alerts', { params }),
  acknowledgeAlert: (id: string) => api.post(`/monitoring/alerts/${id}/acknowledge`),
}

// Standards API - AI员工标准配置
export const standardsApi = {
  list: () => api.get('/standards'),
  get: (agentType: string) => api.get(`/standards/${agentType}`),
  update: (agentType: string, data: any) => api.patch(`/standards/${agentType}`, data),
  reset: (agentType: string) => api.post(`/standards/${agentType}/reset`),
}

// Company API - 公司配置
export const companyApi = {
  get: () => api.get('/company'),
  update: (data: any) => api.patch('/company', data),
}

// Webchat API - 网站聊天
export const webchatApi = {
  createSession: (visitorInfo?: any) => api.post('/webchat/session', visitorInfo),
  sendMessage: (sessionId: string, content: string) =>
    api.post(`/webchat/session/${sessionId}/message`, { content }),
  getHistory: (sessionId: string) => api.get(`/webchat/session/${sessionId}/history`),
  endSession: (sessionId: string) => api.post(`/webchat/session/${sessionId}/end`),
}

export default api
