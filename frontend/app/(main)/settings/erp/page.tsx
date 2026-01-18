'use client'

import { useState, useEffect } from 'react'
import { 
  Database, 
  Shield, 
  CheckCircle, 
  XCircle, 
  RefreshCw, 
  Trash2, 
  Eye, 
  EyeOff,
  Loader2,
  AlertTriangle,
  Clock,
  Activity,
  Package,
  FileText,
  Users,
  Truck,
  DollarSign
} from 'lucide-react'

interface ERPConfig {
  id?: string
  api_url: string
  auth_type: string
  auth_token: string
  username?: string
  description?: string
  is_active?: boolean
  created_at?: string
  updated_at?: string
  has_token?: boolean  // 标记是否已有密钥保存
}

interface SyncLog {
  id: string
  endpoint: string
  params?: string
  success: boolean
  error?: string
  created_at?: string
}

interface TestResult {
  success: boolean
  message?: string
  error?: string
  api_url?: string
}

export default function ERPSettingsPage() {
  const [config, setConfig] = useState<ERPConfig>({
    api_url: 'https://api.xianfeng-eu.com',
    auth_type: 'bearer',
    auth_token: '',
    username: '',
    description: 'BP Logistics ERP'
  })
  
  const [logs, setLogs] = useState<SyncLog[]>([])
  const [showToken, setShowToken] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [isClearingCache, setIsClearingCache] = useState(false)
  
  // 加载配置和日志
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 获取配置
        const configRes = await fetch('/api/erp/config')
        if (configRes.ok) {
          const data = await configRes.json()
          if (data.api_url) {
            setConfig(prev => ({
              ...prev,
              api_url: data.api_url || prev.api_url,
              auth_type: data.auth_type || prev.auth_type,
              username: data.username || '',
              description: data.description || prev.description,
              has_token: data.has_token || false  // 标记是否已有密钥
            }))
          }
        }
        
        // 获取日志
        const logsRes = await fetch('/api/erp/logs?limit=20')
        if (logsRes.ok) {
          const logsData = await logsRes.json()
          setLogs(logsData)
        }
      } catch (error) {
        console.error('加载ERP配置失败:', error)
      } finally {
        setIsLoading(false)
      }
    }
    
    fetchData()
  }, [])
  
  // 保存配置
  const handleSave = async () => {
    // 如果没有已保存的token且当前输入也为空，则提示
    if (!config.api_url || (!config.auth_token && !config.has_token)) {
      alert('请填写API地址和认证令牌')
      return
    }
    
    setIsSaving(true)
    try {
      // 如果已有token且用户没有输入新token，发送特殊标记
      const payload = {
        ...config,
        auth_token: config.auth_token || (config.has_token ? '__KEEP_EXISTING__' : '')
      }
      
      const res = await fetch('/api/erp/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      
      if (res.ok) {
        alert('ERP配置已保存！')
        setTestResult(null)
        // 更新状态，标记已有token
        setConfig(prev => ({ ...prev, auth_token: '', has_token: true }))
      } else {
        throw new Error('保存失败')
      }
    } catch (error) {
      console.error('保存配置失败:', error)
      alert('保存配置失败，请重试')
    } finally {
      setIsSaving(false)
    }
  }
  
  // 测试连接
  const handleTestConnection = async () => {
    setIsTesting(true)
    setTestResult(null)
    
    try {
      const res = await fetch('/api/erp/test-connection', {
        method: 'POST'
      })
      
      const result = await res.json()
      setTestResult(result)
    } catch (error) {
      setTestResult({
        success: false,
        error: '连接测试失败'
      })
    } finally {
      setIsTesting(false)
    }
  }
  
  // 清除缓存
  const handleClearCache = async () => {
    if (!confirm('确定要清除所有ERP数据缓存吗？')) return
    
    setIsClearingCache(true)
    try {
      const res = await fetch('/api/erp/clear-cache', {
        method: 'POST'
      })
      
      if (res.ok) {
        alert('缓存已清除')
      } else {
        throw new Error('清除失败')
      }
    } catch (error) {
      alert('清除缓存失败')
    } finally {
      setIsClearingCache(false)
    }
  }
  
  // 刷新日志
  const refreshLogs = async () => {
    try {
      const res = await fetch('/api/erp/logs?limit=20')
      if (res.ok) {
        const data = await res.json()
        setLogs(data)
      }
    } catch (error) {
      console.error('刷新日志失败:', error)
    }
  }
  
  if (isLoading) {
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
            <Database className="w-7 h-7 text-cyber-blue" />
            ERP系统对接
          </h1>
          <p className="text-gray-400 mt-1">连接BP Logistics ERP系统，获取业务数据</p>
        </div>
      </div>
      
      {/* 安全提示 */}
      <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-start gap-3">
        <Shield className="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" />
        <div>
          <h3 className="text-emerald-400 font-medium">安全模式：只读访问</h3>
          <p className="text-emerald-300/70 text-sm mt-1">
            系统只能从ERP获取数据，无法进行任何修改、创建或删除操作。请确保在ERP系统中创建一个只读权限的API账户。
          </p>
        </div>
      </div>
      
      {/* 可获取的数据类型 */}
      <div className="bg-dark-purple/40 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">可获取的业务数据（基于BP Logistics ERP内部API）</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { icon: Package, label: '订单管理', desc: '订单列表、详情、统计' },
            { icon: FileText, label: '发票管理', desc: '发票列表、详情' },
            { icon: DollarSign, label: '付款记录', desc: '付款列表、详情' },
            { icon: Activity, label: '综合统计', desc: '业务数据统计' },
            { icon: Clock, label: '财务汇总', desc: '财务概览数据' },
            { icon: Users, label: '月度报表', desc: '月度统计分析' }
          ].map((item, index) => (
            <div key={index} className="bg-deep-space/50 rounded-lg p-4 text-center">
              <item.icon className="w-8 h-8 text-cyber-blue mx-auto mb-2" />
              <div className="text-white font-medium text-sm">{item.label}</div>
              <div className="text-gray-500 text-xs mt-1">{item.desc}</div>
            </div>
          ))}
        </div>
      </div>
      
      {/* 连接配置 */}
      <div className="bg-dark-purple/40 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">连接配置</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">API地址</label>
            <input
              type="text"
              value={config.api_url}
              onChange={e => setConfig(prev => ({ ...prev, api_url: e.target.value }))}
              className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              placeholder="https://api.xianfeng-eu.com"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">认证类型</label>
            <select
              value={config.auth_type}
              onChange={e => setConfig(prev => ({ ...prev, auth_type: e.target.value }))}
              className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
            >
              <option value="bearer">Authorization: Bearer Token</option>
              <option value="x_api_key">X-API-Key Header</option>
              <option value="api_key">Api-Key Header</option>
              <option value="apikey">apikey Header（小写）</option>
              <option value="query_param">URL参数: ?api_key=xxx</option>
            </select>
            <p className="text-gray-500 text-xs mt-1">请根据ERP API文档选择正确的认证方式</p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">认证令牌/密钥</label>
            <div className="relative">
              <input
                type={showToken ? 'text' : 'password'}
                value={config.auth_token}
                onChange={e => setConfig(prev => ({ ...prev, auth_token: e.target.value, has_token: false }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none pr-12"
                placeholder={config.has_token ? '••••••••（已保存，输入新密钥可覆盖）' : '请输入API Token或密钥'}
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
              >
                {showToken ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            {config.has_token && !config.auth_token && (
              <p className="text-emerald-400 text-xs mt-1 flex items-center gap-1">
                <CheckCircle className="w-3 h-3" />
                密钥已保存，留空则保持不变
              </p>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">客户端ID（可选）</label>
            <input
              type="text"
              value={config.username || ''}
              onChange={e => setConfig(prev => ({ ...prev, username: e.target.value }))}
              className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              placeholder="如: readonly_client"
            />
          </div>
        </div>
        
        <div className="mt-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">配置描述</label>
          <input
            type="text"
            value={config.description || ''}
            onChange={e => setConfig(prev => ({ ...prev, description: e.target.value }))}
            className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
            placeholder="BP Logistics ERP 只读账户"
          />
        </div>
        
        {/* 操作按钮 */}
        <div className="flex items-center gap-4 mt-6">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
            {isSaving ? '保存中...' : '保存配置'}
          </button>
          
          <button
            onClick={handleTestConnection}
            disabled={isTesting}
            className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-white font-medium transition-colors disabled:opacity-50"
          >
            {isTesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
            {isTesting ? '测试中...' : '测试连接'}
          </button>
          
          <button
            onClick={handleClearCache}
            disabled={isClearingCache}
            className="flex items-center gap-2 px-6 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-white font-medium transition-colors disabled:opacity-50"
          >
            {isClearingCache ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            清除缓存
          </button>
        </div>
        
        {/* 测试结果 */}
        {testResult && (
          <div className={`mt-4 p-4 rounded-lg flex items-center gap-3 ${
            testResult.success 
              ? 'bg-emerald-500/10 border border-emerald-500/30' 
              : 'bg-red-500/10 border border-red-500/30'
          }`}>
            {testResult.success ? (
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            ) : (
              <XCircle className="w-5 h-5 text-red-400" />
            )}
            <div>
              <span className={testResult.success ? 'text-emerald-400' : 'text-red-400'}>
                {testResult.success ? testResult.message : testResult.error}
              </span>
              {testResult.api_url && (
                <span className="text-gray-400 text-sm ml-2">({testResult.api_url})</span>
              )}
            </div>
          </div>
        )}
      </div>
      
      {/* 同步日志 */}
      <div className="bg-dark-purple/40 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-gray-400" />
            同步日志
          </h2>
          <button
            onClick={refreshLogs}
            className="flex items-center gap-2 px-4 py-2 text-gray-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>
        
        {logs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                  <th className="pb-3 font-medium">时间</th>
                  <th className="pb-3 font-medium">端点</th>
                  <th className="pb-3 font-medium">状态</th>
                  <th className="pb-3 font-medium">详情</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-gray-800 text-sm">
                    <td className="py-3 text-gray-400">
                      {log.created_at ? new Date(log.created_at).toLocaleString('zh-CN') : '-'}
                    </td>
                    <td className="py-3 text-white font-mono text-xs">{log.endpoint}</td>
                    <td className="py-3">
                      {log.success ? (
                        <span className="flex items-center gap-1 text-emerald-400">
                          <CheckCircle className="w-4 h-4" />
                          成功
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-red-400">
                          <XCircle className="w-4 h-4" />
                          失败
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-gray-400 text-xs max-w-xs truncate">
                      {log.error || log.params || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            <Clock className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>暂无同步日志</p>
            <p className="text-sm mt-1">配置ERP连接后，API调用记录将显示在这里</p>
          </div>
        )}
      </div>
      
      {/* 使用说明 */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="text-amber-400 font-medium">配置说明</h3>
            <ul className="text-amber-300/70 text-sm mt-2 space-y-1 list-disc list-inside">
              <li>请在ERP系统中创建一个<strong>只读权限</strong>的API账户</li>
              <li>确保该账户只能执行GET请求，无法进行任何数据修改</li>
              <li>API Token应定期更换以确保安全</li>
              <li>数据会自动缓存5分钟，减少API调用频率</li>
              <li>AI员工将使用这些数据回答客户关于订单、报价等问题</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
