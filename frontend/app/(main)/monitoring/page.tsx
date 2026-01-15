'use client'

import { useState, useEffect, useCallback } from 'react'
import { Activity, Server, Shield, Database, RefreshCw, CheckCircle, XCircle, AlertTriangle, Clock, Users, MessageSquare, Video, Loader2 } from 'lucide-react'

interface ApiStatus {
  api_name: string
  status: string
  response_time_ms: number | null
  last_check: string
  error_message: string | null
}

interface CertificateStatus {
  domain: string
  issuer: string
  expires_at: string
  days_until_expiry: number
  status: string
}

interface AgentPerformance {
  agent_type: string
  agent_name: string
  tasks_today: number
  tasks_completed_today: number
  tasks_failed_today: number
  success_rate: number
  avg_response_time_ms: number | null
  status: string
}

interface SystemOverview {
  total_customers: number
  new_customers_today: number
  total_conversations: number
  conversations_today: number
  total_videos: number
  videos_today: number
  system_uptime_hours: number
}

const statusColors: Record<string, string> = {
  healthy: 'text-green-400',
  available: 'text-green-400',
  valid: 'text-green-400',
  online: 'text-green-400',
  degraded: 'text-yellow-400',
  warning: 'text-yellow-400',
  expiring_soon: 'text-yellow-400',
  busy: 'text-yellow-400',
  unavailable: 'text-red-400',
  unhealthy: 'text-red-400',
  expired: 'text-red-400',
  error: 'text-red-400',
  timeout: 'text-red-400',
  offline: 'text-gray-400'
}

const statusBgColors: Record<string, string> = {
  healthy: 'bg-green-400/10',
  available: 'bg-green-400/10',
  valid: 'bg-green-400/10',
  online: 'bg-green-400/10',
  degraded: 'bg-yellow-400/10',
  warning: 'bg-yellow-400/10',
  expiring_soon: 'bg-yellow-400/10',
  busy: 'bg-yellow-400/10',
  unavailable: 'bg-red-400/10',
  unhealthy: 'bg-red-400/10',
  expired: 'bg-red-400/10',
  error: 'bg-red-400/10',
  timeout: 'bg-red-400/10',
  offline: 'bg-gray-400/10'
}

const StatusIcon = ({ status }: { status: string }) => {
  if (['healthy', 'available', 'valid', 'online'].includes(status)) {
    return <CheckCircle className="w-5 h-5 text-green-400" />
  }
  if (['degraded', 'warning', 'expiring_soon', 'busy'].includes(status)) {
    return <AlertTriangle className="w-5 h-5 text-yellow-400" />
  }
  return <XCircle className="w-5 h-5 text-red-400" />
}

export default function MonitoringPage() {
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<string>('')
  
  const [overview, setOverview] = useState<SystemOverview | null>(null)
  const [apis, setApis] = useState<ApiStatus[]>([])
  const [certificates, setCertificates] = useState<CertificateStatus[]>([])
  const [agents, setAgents] = useState<AgentPerformance[]>([])

  // 获取系统概览
  const fetchOverview = async () => {
    try {
      const res = await fetch('/api/monitoring/overview')
      if (res.ok) {
        const data = await res.json()
        setOverview(data)
      }
    } catch (error) {
      console.error('获取系统概览失败:', error)
    }
  }

  // 获取API状态
  const fetchApiStatus = async () => {
    try {
      const res = await fetch('/api/monitoring/api-status')
      if (res.ok) {
        const data = await res.json()
        setApis(data)
      }
    } catch (error) {
      console.error('获取API状态失败:', error)
    }
  }

  // 获取证书状态
  const fetchCertificates = async () => {
    try {
      const res = await fetch('/api/monitoring/certificates')
      if (res.ok) {
        const data = await res.json()
        setCertificates(data)
      }
    } catch (error) {
      console.error('获取证书状态失败:', error)
    }
  }

  // 获取AI员工性能
  const fetchAgentPerformance = async () => {
    try {
      const res = await fetch('/api/monitoring/agents')
      if (res.ok) {
        const data = await res.json()
        setAgents(data)
      }
    } catch (error) {
      console.error('获取AI员工性能失败:', error)
    }
  }

  // 刷新所有数据
  const refreshAll = useCallback(async () => {
    setIsRefreshing(true)
    await Promise.all([
      fetchOverview(),
      fetchApiStatus(),
      fetchCertificates(),
      fetchAgentPerformance()
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

  // 计算整体状态
  const getOverallStatus = () => {
    const errorApis = apis.filter(a => ['unavailable', 'error', 'timeout'].includes(a.status))
    const expiredCerts = certificates.filter(c => c.status === 'expired')
    
    if (errorApis.length > 0 || expiredCerts.length > 0) return 'critical'
    
    const warningApis = apis.filter(a => a.status === 'degraded')
    const expiringCerts = certificates.filter(c => c.status === 'expiring_soon')
    
    if (warningApis.length > 0 || expiringCerts.length > 0) return 'warning'
    
    return 'healthy'
  }

  const overallStatus = getOverallStatus()

  const getOverallStatusText = (status: string) => {
    switch (status) {
      case 'healthy': return '系统运行正常'
      case 'warning': return '部分服务异常'
      case 'critical': return '系统故障'
      default: return '未知状态'
    }
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
            <Activity className="w-7 h-7 text-cyber-blue" />
            系统监控
          </h1>
          <p className="text-gray-400 mt-1">实时监控API状态、证书有效期和系统健康度</p>
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

      {/* 整体状态 */}
      <div className={`p-6 rounded-xl ${statusBgColors[overallStatus]} border border-gray-700`}>
        <div className="flex items-center gap-4">
          <div className={`p-4 rounded-full ${statusBgColors[overallStatus]}`}>
            <StatusIcon status={overallStatus} />
          </div>
          <div>
            <h2 className={`text-xl font-bold ${statusColors[overallStatus]}`}>
              {getOverallStatusText(overallStatus)}
            </h2>
            <p className="text-gray-400">
              {apis.filter(a => a.status === 'healthy' || a.status === 'available').length}/{apis.length} 个API正常运行
            </p>
          </div>
        </div>
      </div>

      {/* 系统概览 */}
      {overview && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-dark-purple/40 rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-cyber-blue/20">
              <Users className="w-6 h-6 text-cyber-blue" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{overview.total_customers}</p>
              <p className="text-gray-500 text-sm">总客户 <span className="text-cyber-green">+{overview.new_customers_today}</span></p>
            </div>
          </div>
          <div className="bg-dark-purple/40 rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-neon-purple/20">
              <MessageSquare className="w-6 h-6 text-neon-purple" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{overview.total_conversations}</p>
              <p className="text-gray-500 text-sm">总对话 <span className="text-cyber-green">+{overview.conversations_today}</span></p>
            </div>
          </div>
          <div className="bg-dark-purple/40 rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-energy-orange/20">
              <Video className="w-6 h-6 text-energy-orange" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{overview.total_videos}</p>
              <p className="text-gray-500 text-sm">总视频 <span className="text-cyber-green">+{overview.videos_today}</span></p>
            </div>
          </div>
          <div className="bg-dark-purple/40 rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-cyber-green/20">
              <Clock className="w-6 h-6 text-cyber-green" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{overview.system_uptime_hours.toFixed(1)}h</p>
              <p className="text-gray-500 text-sm">系统运行时间</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API状态 */}
        <div className="bg-dark-purple/40 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <Server className="w-5 h-5 text-cyber-blue" />
            <h2 className="text-lg font-semibold text-white">API服务状态</h2>
          </div>
          <div className="space-y-4">
            {apis.length === 0 ? (
              <p className="text-gray-500 text-center py-4">正在检测API状态...</p>
            ) : (
              apis.map((api, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 bg-deep-space/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <StatusIcon status={api.status} />
                    <div>
                      <p className="text-white font-medium">{api.api_name}</p>
                      {api.error_message && (
                        <p className="text-red-400 text-xs">{api.error_message}</p>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    {api.response_time_ms !== null ? (
                      <p className={`font-mono ${api.response_time_ms > 1000 ? 'text-yellow-400' : 'text-green-400'}`}>
                        {api.response_time_ms}ms
                      </p>
                    ) : (
                      <p className="text-red-400">-</p>
                    )}
                    <p className={`text-xs px-2 py-0.5 rounded-full ${statusColors[api.status]} ${statusBgColors[api.status]}`}>
                      {api.status === 'healthy' || api.status === 'available' ? '正常' : 
                       api.status === 'degraded' ? '降级' : 
                       api.status === 'timeout' ? '超时' : '离线'}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 证书状态 */}
        <div className="bg-dark-purple/40 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <Shield className="w-5 h-5 text-cyber-blue" />
            <h2 className="text-lg font-semibold text-white">SSL证书状态</h2>
          </div>
          <div className="space-y-4">
            {certificates.length === 0 ? (
              <p className="text-gray-500 text-center py-4">正在检测证书状态...</p>
            ) : (
              certificates.map((cert, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 bg-deep-space/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <StatusIcon status={cert.status} />
                    <div>
                      <p className="text-white font-medium">{cert.domain}</p>
                      <p className="text-gray-500 text-xs">颁发机构: {cert.issuer}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-medium ${cert.days_until_expiry < 30 ? 'text-yellow-400' : 'text-green-400'}`}>
                      {cert.days_until_expiry} 天
                    </p>
                    <p className="text-gray-500 text-xs">
                      到期日: {new Date(cert.expires_at).toLocaleDateString('zh-CN')}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* AI员工性能 */}
        <div className="bg-dark-purple/40 rounded-xl p-6 lg:col-span-2">
          <div className="flex items-center gap-3 mb-6">
            <Activity className="w-5 h-5 text-cyber-blue" />
            <h2 className="text-lg font-semibold text-white">AI员工今日性能</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {agents.length === 0 ? (
              <p className="text-gray-500 text-center py-4 col-span-4">正在获取AI员工数据...</p>
            ) : (
              agents.map((agent, index) => (
                <div key={index} className="p-4 bg-deep-space/50 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-white font-medium">{agent.agent_name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[agent.status]} ${statusBgColors[agent.status]}`}>
                      {agent.status === 'online' ? '在线' : agent.status === 'busy' ? '忙碌' : '离线'}
                    </span>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">今日任务</span>
                      <span className="text-cyber-blue font-number">{agent.tasks_today}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">成功率</span>
                      <span className={`font-number ${agent.success_rate >= 80 ? 'text-green-400' : 'text-yellow-400'}`}>
                        {agent.success_rate.toFixed(1)}%
                      </span>
                    </div>
                    {agent.avg_response_time_ms && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">平均响应</span>
                        <span className="text-gray-400 font-number">{agent.avg_response_time_ms.toFixed(0)}ms</span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
