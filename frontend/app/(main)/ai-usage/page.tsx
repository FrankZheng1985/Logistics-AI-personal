'use client'

import { useState, useEffect, useCallback } from 'react'
import { 
  Cpu, DollarSign, Zap, TrendingUp, RefreshCw, 
  AlertTriangle, Bell, Settings, ChevronDown, ChevronUp,
  BarChart3, Clock, CheckCircle, XCircle, Loader2,
  Plus, Trash2, Edit2, Save, X
} from 'lucide-react'

interface UsageStats {
  period: {
    start_date: string
    end_date: string
  }
  summary: {
    total_requests: number
    success_count: number
    error_count: number
    success_rate: number
    total_input_tokens: number
    total_output_tokens: number
    total_tokens: number
    total_cost: number
    avg_response_time_ms: number
    max_response_time_ms: number
  }
  by_provider: Array<{
    provider: string
    requests: number
    tokens: number
    cost: number
  }>
  by_model: Array<{
    provider: string
    model: string
    requests: number
    tokens: number
    cost: number
  }>
  by_agent: Array<{
    agent: string
    requests: number
    tokens: number
    cost: number
  }>
  daily_trend: Array<{
    date: string
    requests: number
    tokens: number
    cost: number
  }>
}

interface DashboardData {
  today: {
    requests: number
    tokens: number
    cost: number
    success_rate: number
  }
  this_week: {
    requests: number
    tokens: number
    cost: number
  }
  this_month: {
    requests: number
    tokens: number
    cost: number
  }
  by_provider: Array<{
    provider: string
    requests: number
    tokens: number
    cost: number
  }>
  by_agent: Array<{
    agent: string
    requests: number
    tokens: number
    cost: number
  }>
  daily_trend: Array<{
    date: string
    requests: number
    tokens: number
    cost: number
  }>
  alert_status: Array<{
    name: string
    type: string
    threshold: number
    current: number
    percentage: number
    is_triggered: boolean
  }>
}

interface Alert {
  id: number
  alert_name: string
  alert_type: string
  threshold_amount: number
  threshold_tokens: number | null
  notify_wechat: boolean
  notify_email: boolean
  notify_users: string | null
  is_active: boolean
  last_triggered_at: string | null
  trigger_count: number
}

interface UsageLog {
  id: number
  agent_name: string | null
  model_name: string
  provider: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost_estimate: number
  task_type: string | null
  response_time_ms: number | null
  is_success: boolean
  error_message: string | null
  created_at: string
}

const providerNames: Record<string, string> = {
  dashscope: '通义千问',
  openai: 'OpenAI',
  anthropic: 'Claude',
  deepseek: 'DeepSeek'
}

const providerColors: Record<string, string> = {
  dashscope: 'bg-orange-500',
  openai: 'bg-green-500',
  anthropic: 'bg-purple-500',
  deepseek: 'bg-blue-500'
}

const alertTypeNames: Record<string, string> = {
  daily: '每日',
  weekly: '每周',
  monthly: '每月'
}

export default function AIUsagePage() {
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'dashboard' | 'logs' | 'alerts'>('dashboard')
  
  // 数据状态
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [logs, setLogs] = useState<UsageLog[]>([])
  const [logsTotal, setLogsTotal] = useState(0)
  const [logsPage, setLogsPage] = useState(1)
  
  // 告警编辑状态
  const [editingAlert, setEditingAlert] = useState<number | null>(null)
  const [showNewAlert, setShowNewAlert] = useState(false)
  const [newAlert, setNewAlert] = useState({
    alert_name: '',
    alert_type: 'daily',
    threshold_amount: 50,
    notify_wechat: true,
    notify_email: false
  })

  // 获取仪表板数据
  const fetchDashboard = async () => {
    try {
      const res = await fetch('/api/ai-usage/dashboard')
      if (res.ok) {
        const data = await res.json()
        setDashboard(data)
      }
    } catch (error) {
      console.error('获取仪表板数据失败:', error)
    }
  }

  // 获取告警配置
  const fetchAlerts = async () => {
    try {
      const res = await fetch('/api/ai-usage/alerts')
      if (res.ok) {
        const data = await res.json()
        setAlerts(data.alerts || [])
      }
    } catch (error) {
      console.error('获取告警配置失败:', error)
    }
  }

  // 获取用量日志
  const fetchLogs = async (page = 1) => {
    try {
      const res = await fetch(`/api/ai-usage/logs?page=${page}&page_size=20`)
      if (res.ok) {
        const data = await res.json()
        setLogs(data.logs || [])
        setLogsTotal(data.total || 0)
        setLogsPage(page)
      }
    } catch (error) {
      console.error('获取用量日志失败:', error)
    }
  }

  // 刷新所有数据
  const refreshAll = useCallback(async () => {
    setIsRefreshing(true)
    await Promise.all([
      fetchDashboard(),
      fetchAlerts(),
      fetchLogs(1)
    ])
    setLastRefresh(new Date().toLocaleTimeString('zh-CN'))
    setIsRefreshing(false)
    setLoading(false)
  }, [])

  useEffect(() => {
    refreshAll()
    // 每60秒自动刷新
    const interval = setInterval(refreshAll, 60000)
    return () => clearInterval(interval)
  }, [refreshAll])

  // 创建告警
  const createAlert = async () => {
    try {
      const res = await fetch('/api/ai-usage/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAlert)
      })
      if (res.ok) {
        setShowNewAlert(false)
        setNewAlert({
          alert_name: '',
          alert_type: 'daily',
          threshold_amount: 50,
          notify_wechat: true,
          notify_email: false
        })
        await fetchAlerts()
      }
    } catch (error) {
      console.error('创建告警失败:', error)
    }
  }

  // 切换告警状态
  const toggleAlert = async (alertId: number) => {
    try {
      const res = await fetch(`/api/ai-usage/alerts/${alertId}/toggle`, {
        method: 'POST'
      })
      if (res.ok) {
        await fetchAlerts()
      }
    } catch (error) {
      console.error('切换告警状态失败:', error)
    }
  }

  // 删除告警
  const deleteAlert = async (alertId: number) => {
    if (!confirm('确定要删除这个告警配置吗？')) return
    
    try {
      const res = await fetch(`/api/ai-usage/alerts/${alertId}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        await fetchAlerts()
      }
    } catch (error) {
      console.error('删除告警失败:', error)
    }
  }

  // 格式化数字
  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toString()
  }

  // 格式化费用
  const formatCost = (cost: number) => {
    return '¥' + cost.toFixed(2)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-cyber-blue" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Cpu className="w-7 h-7 text-cyber-blue" />
            AI用量监控
          </h1>
          <p className="text-gray-400 mt-1">监控大模型API调用用量、费用估算和告警管理</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-gray-500 text-sm">
            上次刷新: {lastRefresh || '-'}
          </span>
          <button
            onClick={refreshAll}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-dark-purple/40 hover:bg-white/10 rounded-lg text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {/* 标签页切换 */}
      <div className="flex gap-2 border-b border-gray-700 pb-2">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeTab === 'dashboard' 
              ? 'bg-cyber-blue text-white' 
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <BarChart3 className="w-4 h-4 inline-block mr-2" />
          统计概览
        </button>
        <button
          onClick={() => { setActiveTab('logs'); fetchLogs(1); }}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeTab === 'logs' 
              ? 'bg-cyber-blue text-white' 
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Clock className="w-4 h-4 inline-block mr-2" />
          调用日志
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeTab === 'alerts' 
              ? 'bg-cyber-blue text-white' 
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Bell className="w-4 h-4 inline-block mr-2" />
          费用告警
        </button>
      </div>

      {/* 统计概览标签页 */}
      {activeTab === 'dashboard' && dashboard && (
        <>
          {/* 费用概览卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gradient-to-br from-cyber-blue/20 to-dark-purple/40 rounded-xl p-6 border border-cyber-blue/30">
              <div className="flex items-center justify-between mb-4">
                <span className="text-gray-400">今日费用</span>
                <DollarSign className="w-5 h-5 text-cyber-blue" />
              </div>
              <p className="text-3xl font-bold text-white">{formatCost(dashboard.today.cost)}</p>
              <div className="mt-2 flex items-center gap-4 text-sm">
                <span className="text-gray-500">{formatNumber(dashboard.today.tokens)} tokens</span>
                <span className="text-gray-500">{dashboard.today.requests} 次调用</span>
              </div>
            </div>

            <div className="bg-gradient-to-br from-neon-purple/20 to-dark-purple/40 rounded-xl p-6 border border-neon-purple/30">
              <div className="flex items-center justify-between mb-4">
                <span className="text-gray-400">本周费用</span>
                <TrendingUp className="w-5 h-5 text-neon-purple" />
              </div>
              <p className="text-3xl font-bold text-white">{formatCost(dashboard.this_week.cost)}</p>
              <div className="mt-2 flex items-center gap-4 text-sm">
                <span className="text-gray-500">{formatNumber(dashboard.this_week.tokens)} tokens</span>
                <span className="text-gray-500">{dashboard.this_week.requests} 次调用</span>
              </div>
            </div>

            <div className="bg-gradient-to-br from-energy-orange/20 to-dark-purple/40 rounded-xl p-6 border border-energy-orange/30">
              <div className="flex items-center justify-between mb-4">
                <span className="text-gray-400">本月费用</span>
                <BarChart3 className="w-5 h-5 text-energy-orange" />
              </div>
              <p className="text-3xl font-bold text-white">{formatCost(dashboard.this_month.cost)}</p>
              <div className="mt-2 flex items-center gap-4 text-sm">
                <span className="text-gray-500">{formatNumber(dashboard.this_month.tokens)} tokens</span>
                <span className="text-gray-500">{dashboard.this_month.requests} 次调用</span>
              </div>
            </div>
          </div>

          {/* 告警状态 */}
          {dashboard.alert_status.length > 0 && (
            <div className="bg-dark-purple/40 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                费用告警状态
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {dashboard.alert_status.map((alert, index) => (
                  <div key={index} className={`p-4 rounded-lg ${
                    alert.is_triggered 
                      ? 'bg-red-500/20 border border-red-500/50' 
                      : alert.percentage > 80 
                        ? 'bg-yellow-500/20 border border-yellow-500/50'
                        : 'bg-green-500/10 border border-green-500/30'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white font-medium">{alert.name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        alert.is_triggered 
                          ? 'bg-red-500/30 text-red-400' 
                          : 'bg-green-500/30 text-green-400'
                      }`}>
                        {alert.is_triggered ? '已触发' : '正常'}
                      </span>
                    </div>
                    <div className="mb-2">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-400">{alertTypeNames[alert.type]}用量</span>
                        <span className="text-white">{formatCost(alert.current)} / {formatCost(alert.threshold)}</span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full transition-all ${
                            alert.is_triggered ? 'bg-red-500' : 
                            alert.percentage > 80 ? 'bg-yellow-500' : 'bg-green-500'
                          }`}
                          style={{ width: `${Math.min(alert.percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                    <p className="text-xs text-gray-500">{alert.percentage.toFixed(1)}% 已使用</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 按提供商统计 */}
            <div className="bg-dark-purple/40 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">按提供商统计</h3>
              {dashboard.by_provider.length === 0 ? (
                <p className="text-gray-500 text-center py-8">暂无数据</p>
              ) : (
                <div className="space-y-4">
                  {dashboard.by_provider.map((item, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-deep-space/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${providerColors[item.provider] || 'bg-gray-500'}`} />
                        <span className="text-white">{providerNames[item.provider] || item.provider}</span>
                      </div>
                      <div className="text-right">
                        <p className="text-white font-medium">{formatCost(item.cost)}</p>
                        <p className="text-gray-500 text-xs">{formatNumber(item.tokens)} tokens</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 按AI员工统计 */}
            <div className="bg-dark-purple/40 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">按AI员工统计</h3>
              {dashboard.by_agent.length === 0 ? (
                <p className="text-gray-500 text-center py-8">暂无数据</p>
              ) : (
                <div className="space-y-4">
                  {dashboard.by_agent.map((item, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-deep-space/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-cyber-blue/20 flex items-center justify-center">
                          <Zap className="w-4 h-4 text-cyber-blue" />
                        </div>
                        <span className="text-white">{item.agent}</span>
                      </div>
                      <div className="text-right">
                        <p className="text-white font-medium">{formatCost(item.cost)}</p>
                        <p className="text-gray-500 text-xs">{item.requests} 次调用</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 费用趋势图 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">费用趋势（本月）</h3>
            {dashboard.daily_trend.length === 0 ? (
              <p className="text-gray-500 text-center py-8">暂无数据</p>
            ) : (
              <div className="h-48">
                <div className="flex items-end justify-between h-40 gap-1">
                  {dashboard.daily_trend.map((item, index) => {
                    const maxCost = Math.max(...dashboard.daily_trend.map(d => d.cost), 1)
                    const height = (item.cost / maxCost) * 100
                    return (
                      <div key={index} className="flex-1 flex flex-col items-center group">
                        <div className="relative w-full">
                          <div
                            className="w-full bg-cyber-blue/60 rounded-t transition-all group-hover:bg-cyber-blue"
                            style={{ height: `${Math.max(height, 2)}%`, minHeight: '2px' }}
                          />
                          <div className="absolute -top-8 left-1/2 -translate-x-1/2 hidden group-hover:block bg-gray-800 px-2 py-1 rounded text-xs text-white whitespace-nowrap z-10">
                            {formatCost(item.cost)}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
                <div className="flex justify-between mt-2 text-xs text-gray-500">
                  <span>{dashboard.daily_trend[0]?.date?.split('-').slice(1).join('/')}</span>
                  <span>{dashboard.daily_trend[dashboard.daily_trend.length - 1]?.date?.split('-').slice(1).join('/')}</span>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* 调用日志标签页 */}
      {activeTab === 'logs' && (
        <div className="bg-dark-purple/40 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">API调用日志</h3>
            <span className="text-gray-500 text-sm">共 {logsTotal} 条记录</span>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                  <th className="pb-3 pr-4">时间</th>
                  <th className="pb-3 pr-4">AI员工</th>
                  <th className="pb-3 pr-4">模型</th>
                  <th className="pb-3 pr-4">Tokens</th>
                  <th className="pb-3 pr-4">费用</th>
                  <th className="pb-3 pr-4">响应时间</th>
                  <th className="pb-3">状态</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center text-gray-500 py-8">暂无数据</td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="border-b border-gray-700/50 hover:bg-white/5">
                      <td className="py-3 pr-4 text-gray-400 text-sm">
                        {new Date(log.created_at).toLocaleString('zh-CN', { 
                          month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' 
                        })}
                      </td>
                      <td className="py-3 pr-4 text-white">{log.agent_name || '-'}</td>
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${providerColors[log.provider] || 'bg-gray-500'}`} />
                          <span className="text-white text-sm">{log.model_name}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-gray-300 font-mono text-sm">
                        <span className="text-green-400">{log.input_tokens}</span>
                        <span className="text-gray-500"> + </span>
                        <span className="text-blue-400">{log.output_tokens}</span>
                      </td>
                      <td className="py-3 pr-4 text-yellow-400 font-mono text-sm">
                        {formatCost(log.cost_estimate)}
                      </td>
                      <td className="py-3 pr-4 text-gray-400 font-mono text-sm">
                        {log.response_time_ms ? `${log.response_time_ms}ms` : '-'}
                      </td>
                      <td className="py-3">
                        {log.is_success ? (
                          <span className="flex items-center gap-1 text-green-400 text-sm">
                            <CheckCircle className="w-4 h-4" />
                            成功
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-red-400 text-sm" title={log.error_message || ''}>
                            <XCircle className="w-4 h-4" />
                            失败
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          
          {/* 分页 */}
          {logsTotal > 20 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <button
                onClick={() => fetchLogs(logsPage - 1)}
                disabled={logsPage <= 1}
                className="px-3 py-1 rounded bg-white/10 text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              <span className="text-gray-400 px-4">
                第 {logsPage} 页 / 共 {Math.ceil(logsTotal / 20)} 页
              </span>
              <button
                onClick={() => fetchLogs(logsPage + 1)}
                disabled={logsPage >= Math.ceil(logsTotal / 20)}
                className="px-3 py-1 rounded bg-white/10 text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          )}
        </div>
      )}

      {/* 费用告警标签页 */}
      {activeTab === 'alerts' && (
        <div className="space-y-6">
          {/* 告警配置列表 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">告警配置</h3>
              <button
                onClick={() => setShowNewAlert(true)}
                className="flex items-center gap-2 px-4 py-2 bg-cyber-blue hover:bg-cyber-blue/80 rounded-lg text-white transition-colors"
              >
                <Plus className="w-4 h-4" />
                新建告警
              </button>
            </div>

            {/* 新建告警表单 */}
            {showNewAlert && (
              <div className="mb-4 p-4 bg-deep-space/50 rounded-lg border border-cyber-blue/30">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-gray-400 text-sm mb-1">告警名称</label>
                    <input
                      type="text"
                      value={newAlert.alert_name}
                      onChange={(e) => setNewAlert({ ...newAlert, alert_name: e.target.value })}
                      placeholder="例：每日费用告警"
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1">告警类型</label>
                    <select
                      value={newAlert.alert_type}
                      onChange={(e) => setNewAlert({ ...newAlert, alert_type: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                    >
                      <option value="daily">每日告警</option>
                      <option value="weekly">每周告警</option>
                      <option value="monthly">每月告警</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1">阈值金额（元）</label>
                    <input
                      type="number"
                      value={newAlert.threshold_amount}
                      onChange={(e) => setNewAlert({ ...newAlert, threshold_amount: parseFloat(e.target.value) })}
                      min="0"
                      step="10"
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-6 mt-4">
                  <label className="flex items-center gap-2 text-gray-400">
                    <input
                      type="checkbox"
                      checked={newAlert.notify_wechat}
                      onChange={(e) => setNewAlert({ ...newAlert, notify_wechat: e.target.checked })}
                      className="rounded border-gray-600 bg-gray-800 text-cyber-blue focus:ring-cyber-blue"
                    />
                    企业微信通知
                  </label>
                  <label className="flex items-center gap-2 text-gray-400">
                    <input
                      type="checkbox"
                      checked={newAlert.notify_email}
                      onChange={(e) => setNewAlert({ ...newAlert, notify_email: e.target.checked })}
                      className="rounded border-gray-600 bg-gray-800 text-cyber-blue focus:ring-cyber-blue"
                    />
                    邮件通知
                  </label>
                </div>
                <div className="flex justify-end gap-2 mt-4">
                  <button
                    onClick={() => setShowNewAlert(false)}
                    className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={createAlert}
                    disabled={!newAlert.alert_name || newAlert.threshold_amount <= 0}
                    className="px-4 py-2 bg-cyber-blue hover:bg-cyber-blue/80 rounded-lg text-white transition-colors disabled:opacity-50"
                  >
                    创建
                  </button>
                </div>
              </div>
            )}

            {/* 告警列表 */}
            <div className="space-y-3">
              {alerts.length === 0 ? (
                <p className="text-gray-500 text-center py-8">暂无告警配置，点击上方按钮新建</p>
              ) : (
                alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-4 rounded-lg border ${
                      alert.is_active 
                        ? 'bg-deep-space/50 border-gray-700' 
                        : 'bg-gray-800/30 border-gray-800 opacity-60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${alert.is_active ? 'bg-cyber-blue/20' : 'bg-gray-700'}`}>
                          <Bell className={`w-5 h-5 ${alert.is_active ? 'text-cyber-blue' : 'text-gray-500'}`} />
                        </div>
                        <div>
                          <h4 className="text-white font-medium">{alert.alert_name}</h4>
                          <p className="text-gray-500 text-sm">
                            {alertTypeNames[alert.alert_type]}费用超过 {formatCost(alert.threshold_amount)} 时触发
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right text-sm">
                          <p className="text-gray-400">
                            触发 {alert.trigger_count} 次
                          </p>
                          {alert.last_triggered_at && (
                            <p className="text-gray-500 text-xs">
                              上次: {new Date(alert.last_triggered_at).toLocaleDateString('zh-CN')}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => toggleAlert(alert.id)}
                            className={`px-3 py-1 rounded text-sm transition-colors ${
                              alert.is_active 
                                ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30' 
                                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                            }`}
                          >
                            {alert.is_active ? '已启用' : '已禁用'}
                          </button>
                          <button
                            onClick={() => deleteAlert(alert.id)}
                            className="p-2 text-gray-500 hover:text-red-400 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                    {/* 通知方式 */}
                    <div className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-700">
                      <span className="text-gray-500 text-sm">通知方式:</span>
                      {alert.notify_wechat && (
                        <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded">企业微信</span>
                      )}
                      {alert.notify_email && (
                        <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">邮件</span>
                      )}
                      {!alert.notify_wechat && !alert.notify_email && (
                        <span className="text-xs text-gray-500">未配置</span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 使用说明 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5 text-gray-400" />
              使用说明
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-400">
              <div className="p-4 bg-deep-space/50 rounded-lg">
                <h4 className="text-white font-medium mb-2">每日告警</h4>
                <p>监控当天的API调用费用，超过阈值时触发通知。每天最多触发一次。</p>
              </div>
              <div className="p-4 bg-deep-space/50 rounded-lg">
                <h4 className="text-white font-medium mb-2">每周告警</h4>
                <p>监控本周（周一至今）的累计费用，超过阈值时触发通知。每周最多触发一次。</p>
              </div>
              <div className="p-4 bg-deep-space/50 rounded-lg">
                <h4 className="text-white font-medium mb-2">每月告警</h4>
                <p>监控本月累计费用，超过阈值时触发通知。每月最多触发一次。</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
