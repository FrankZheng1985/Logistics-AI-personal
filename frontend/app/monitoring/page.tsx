'use client'

import { useState, useEffect } from 'react'
import { Activity, Server, Shield, Database, RefreshCw, CheckCircle, XCircle, AlertTriangle, Clock } from 'lucide-react'

interface ApiStatus {
  name: string
  status: 'available' | 'degraded' | 'unavailable'
  response_time_ms: number | null
  last_check: string
  error?: string
}

interface CertificateStatus {
  domain: string
  status: 'valid' | 'expiring_soon' | 'expired'
  days_until_expiry: number
  issuer: string
  valid_until: string
}

interface SystemHealth {
  overall_status: 'healthy' | 'warning' | 'critical'
  apis: ApiStatus[]
  certificates: CertificateStatus[]
  database: {
    status: 'healthy' | 'unhealthy'
    response_time_ms: number
  }
}

// 初始化时使用固定时间戳，避免水合错误
const getInitialHealth = (): SystemHealth => ({
  overall_status: 'healthy',
  apis: [
    { name: '可灵AI视频', status: 'available', response_time_ms: 245, last_check: '' },
    { name: '通义千问', status: 'available', response_time_ms: 156, last_check: '' },
    { name: 'Serper搜索', status: 'degraded', response_time_ms: 1250, last_check: '', error: '响应较慢' },
    { name: 'SMTP邮件', status: 'available', response_time_ms: 89, last_check: '' }
  ],
  certificates: [
    { domain: 'api.klingai.com', status: 'valid', days_until_expiry: 245, issuer: 'DigiCert', valid_until: '2026-09-15' },
    { domain: 'dashscope.aliyuncs.com', status: 'valid', days_until_expiry: 180, issuer: 'GlobalSign', valid_until: '2026-07-10' }
  ],
  database: {
    status: 'healthy',
    response_time_ms: 12
  }
})

const statusColors = {
  available: 'text-green-400',
  healthy: 'text-green-400',
  valid: 'text-green-400',
  degraded: 'text-yellow-400',
  warning: 'text-yellow-400',
  expiring_soon: 'text-yellow-400',
  unavailable: 'text-red-400',
  unhealthy: 'text-red-400',
  expired: 'text-red-400',
  critical: 'text-red-400'
}

const statusBgColors = {
  available: 'bg-green-400/10',
  healthy: 'bg-green-400/10',
  valid: 'bg-green-400/10',
  degraded: 'bg-yellow-400/10',
  warning: 'bg-yellow-400/10',
  expiring_soon: 'bg-yellow-400/10',
  unavailable: 'bg-red-400/10',
  unhealthy: 'bg-red-400/10',
  expired: 'bg-red-400/10',
  critical: 'bg-red-400/10'
}

const StatusIcon = ({ status }: { status: string }) => {
  if (status === 'available' || status === 'healthy' || status === 'valid') {
    return <CheckCircle className="w-5 h-5 text-green-400" />
  }
  if (status === 'degraded' || status === 'warning' || status === 'expiring_soon') {
    return <AlertTriangle className="w-5 h-5 text-yellow-400" />
  }
  return <XCircle className="w-5 h-5 text-red-400" />
}

export default function MonitoringPage() {
  const [health, setHealth] = useState<SystemHealth>(getInitialHealth)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<string>('')
  const [mounted, setMounted] = useState(false)

  // 客户端挂载后更新时间
  useEffect(() => {
    setMounted(true)
    setLastRefresh(new Date().toLocaleTimeString())
    // 更新 API 的 last_check 时间
    setHealth(prev => ({
      ...prev,
      apis: prev.apis.map(api => ({
        ...api,
        last_check: new Date().toISOString()
      }))
    }))
  }, [])

  const refresh = async () => {
    setIsRefreshing(true)
    // 模拟刷新
    await new Promise(resolve => setTimeout(resolve, 1500))
    setLastRefresh(new Date().toLocaleTimeString())
    setIsRefreshing(false)
  }

  // 避免水合错误，在客户端挂载前不渲染动态内容
  if (!mounted) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 animate-spin text-cyber-blue" />
      </div>
    )
  }

  const getOverallStatusText = (status: string) => {
    switch (status) {
      case 'healthy': return '系统运行正常'
      case 'warning': return '部分服务异常'
      case 'critical': return '系统故障'
      default: return '未知状态'
    }
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
            上次刷新: {lastRefresh}
          </span>
          <button
            onClick={refresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-dark-purple/40 hover:bg-white/10 rounded-lg text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {/* 整体状态 */}
      <div className={`p-6 rounded-xl ${statusBgColors[health.overall_status]} border border-gray-700`}>
        <div className="flex items-center gap-4">
          <div className={`p-4 rounded-full ${statusBgColors[health.overall_status]}`}>
            <StatusIcon status={health.overall_status} />
          </div>
          <div>
            <h2 className={`text-xl font-bold ${statusColors[health.overall_status]}`}>
              {getOverallStatusText(health.overall_status)}
            </h2>
            <p className="text-gray-400">
              {health.apis.filter(a => a.status === 'available').length}/{health.apis.length} 个API正常运行
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API状态 */}
        <div className="bg-dark-purple/40 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <Server className="w-5 h-5 text-cyber-blue" />
            <h2 className="text-lg font-semibold text-white">API服务状态</h2>
          </div>
          <div className="space-y-4">
            {health.apis.map((api, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 bg-deep-space/50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <StatusIcon status={api.status} />
                  <div>
                    <p className="text-white font-medium">{api.name}</p>
                    {api.error && (
                      <p className="text-yellow-400 text-xs">{api.error}</p>
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
                    {api.status === 'available' ? '正常' : api.status === 'degraded' ? '降级' : '离线'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 证书状态 */}
        <div className="bg-dark-purple/40 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <Shield className="w-5 h-5 text-cyber-blue" />
            <h2 className="text-lg font-semibold text-white">SSL证书状态</h2>
          </div>
          <div className="space-y-4">
            {health.certificates.map((cert, index) => (
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
                  <p className="text-gray-500 text-xs">到期日: {cert.valid_until}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 数据库状态 */}
        <div className="bg-dark-purple/40 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <Database className="w-5 h-5 text-cyber-blue" />
            <h2 className="text-lg font-semibold text-white">数据库状态</h2>
          </div>
          <div className="flex items-center justify-between p-4 bg-deep-space/50 rounded-lg">
            <div className="flex items-center gap-3">
              <StatusIcon status={health.database.status} />
              <div>
                <p className="text-white font-medium">PostgreSQL</p>
                <p className="text-gray-500 text-xs">主数据库</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-green-400 font-mono">{health.database.response_time_ms}ms</p>
              <p className={`text-xs px-2 py-0.5 rounded-full ${statusColors[health.database.status]} ${statusBgColors[health.database.status]}`}>
                {health.database.status === 'healthy' ? '连接正常' : '连接异常'}
              </p>
            </div>
          </div>
        </div>

        {/* 响应时间趋势 */}
        <div className="bg-dark-purple/40 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <Clock className="w-5 h-5 text-cyber-blue" />
            <h2 className="text-lg font-semibold text-white">响应时间概览</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {health.apis.map((api, index) => (
              <div key={index} className="p-4 bg-deep-space/50 rounded-lg">
                <p className="text-gray-400 text-sm mb-1">{api.name}</p>
                <p className={`text-2xl font-bold ${api.response_time_ms && api.response_time_ms > 1000 ? 'text-yellow-400' : 'text-white'}`}>
                  {api.response_time_ms ?? '-'}
                  <span className="text-sm text-gray-500 ml-1">ms</span>
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
