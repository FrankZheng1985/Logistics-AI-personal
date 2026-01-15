'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { 
  ArrowLeft, 
  Calendar, 
  Users, 
  TrendingUp, 
  MessageSquare, 
  Video, 
  CheckCircle,
  AlertTriangle,
  Lightbulb,
  Bot,
  Clock,
  Star,
  RefreshCw
} from 'lucide-react'
import Link from 'next/link'

interface DailyReport {
  id?: string
  report_date: string
  report_type: string
  summary: string
  agent_stats: {
    date: string
    agents: Record<string, {
      name: string
      total_tasks: number
      success_count: number
      failed_count: number
      success_rate: number
      avg_duration_ms: number
      performance_rating: string
    }>
    total_tasks: number
    total_success: number
    overall_success_rate: number
    active_agents: number
  }
  business_metrics: {
    customers: { new_today: number; high_intent_today: number; total: number }
    leads: { new_today: number; quality_leads_today: number; total: number }
    videos: { created_today: number; completed_today: number; total: number }
    conversations: { total_today: number; unique_customers: number }
  }
  system_health: {
    overall_status: string
    components: Record<string, any>
    issues: string[]
  }
  highlights: Array<{ type: string; title: string; detail: string }>
  issues: Array<{ type: string; severity: string; title: string; detail: string }>
  recommendations: Array<{ priority: string; action: string; detail: string }>
  generation_time_ms: number
  created_at: string
}

export default function ReportDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [report, setReport] = useState<DailyReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchReport = async () => {
      try {
        setLoading(true)
        // 如果是 "latest"，获取最新报告
        const url = params.id === 'latest' 
          ? '/api/reports/daily/latest'
          : `/api/reports/daily/${params.id}`
        
        const res = await fetch(url)
        if (res.ok) {
          const data = await res.json()
          setReport(data)
        } else {
          setError('报告不存在或已删除')
        }
      } catch (err) {
        setError('获取报告失败')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    if (params.id) {
      fetchReport()
    }
  }, [params.id])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-cyber-green'
      case 'warning': return 'text-energy-orange'
      case 'critical': return 'text-alert-red'
      default: return 'text-gray-400'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy': return '健康 ✅'
      case 'warning': return '警告 ⚠️'
      case 'critical': return '严重 🔴'
      case 'degraded': return '降级 ⚠️'
      default: return '未知'
    }
  }

  const getPerformanceColor = (rating: string) => {
    switch (rating) {
      case '优秀': return 'text-cyber-green'
      case '良好': return 'text-cyber-blue'
      case '一般': return 'text-energy-orange'
      case '需改进': return 'text-alert-red'
      default: return 'text-gray-400'
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'border-alert-red bg-alert-red/10'
      case 'medium': return 'border-energy-orange bg-energy-orange/10'
      case 'low': return 'border-cyber-blue bg-cyber-blue/10'
      default: return 'border-gray-500 bg-gray-500/10'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-alert-red/20 text-alert-red'
      case 'medium': return 'bg-energy-orange/20 text-energy-orange'
      case 'low': return 'bg-cyber-blue/20 text-cyber-blue'
      default: return 'bg-gray-500/20 text-gray-400'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 text-cyber-blue animate-spin" />
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="space-y-6">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-gray-400 hover:text-white">
          <ArrowLeft className="w-4 h-4" />
          返回
        </button>
        <div className="glass-card p-12 text-center">
          <AlertTriangle className="w-16 h-16 text-energy-orange mx-auto mb-4" />
          <p className="text-xl text-gray-300">{error || '报告不存在'}</p>
          <Link href="/reports" className="mt-4 inline-block text-cyber-blue hover:underline">
            查看所有报告
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
          <ArrowLeft className="w-4 h-4" />
          返回
        </button>
        <div className="flex items-center gap-4">
          <span className="text-gray-500 text-sm flex items-center gap-1">
            <Clock className="w-4 h-4" />
            生成耗时: {report.generation_time_ms}ms
          </span>
        </div>
      </div>

      {/* 报告标题 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 rounded-lg bg-cyber-blue/10">
            <Calendar className="w-6 h-6 text-cyber-blue" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">📊 {report.report_date} 工作总结</h1>
            <p className="text-gray-400 text-sm mt-1">
              AI团队每日工作汇报 · {report.created_at ? new Date(report.created_at).toLocaleString('zh-CN') : ''}
            </p>
          </div>
        </div>
      </div>

      {/* 核心指标 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <Users className="w-4 h-4" />
            新增客户
          </div>
          <p className="text-3xl font-bold text-cyber-blue">
            {report.business_metrics?.customers?.new_today || 0}
          </p>
        </div>
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <TrendingUp className="w-4 h-4" />
            高意向客户
          </div>
          <p className="text-3xl font-bold text-cyber-green">
            {report.business_metrics?.customers?.high_intent_today || 0}
          </p>
        </div>
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <MessageSquare className="w-4 h-4" />
            对话数量
          </div>
          <p className="text-3xl font-bold text-neon-purple">
            {report.business_metrics?.conversations?.total_today || 0}
          </p>
        </div>
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <Video className="w-4 h-4" />
            视频生成
          </div>
          <p className="text-3xl font-bold text-energy-orange">
            {report.business_metrics?.videos?.created_today || 0}
          </p>
        </div>
      </div>

      {/* 报告摘要 */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Star className="w-5 h-5 text-energy-orange" />
          报告摘要
        </h2>
        <div className="bg-dark-purple/40 rounded-lg p-4 whitespace-pre-wrap text-gray-300">
          {report.summary}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* AI团队表现 */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Bot className="w-5 h-5 text-cyber-blue" />
            AI团队表现
          </h2>
          <div className="space-y-3">
            {report.agent_stats?.agents && Object.entries(report.agent_stats.agents).map(([type, agent]) => (
              <div key={type} className="flex items-center justify-between p-3 bg-dark-purple/40 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center text-sm font-bold">
                    {agent.name[0]}
                  </div>
                  <div>
                    <p className="font-medium">{agent.name}</p>
                    <p className="text-gray-500 text-xs">任务: {agent.total_tasks} | 成功: {agent.success_count}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`font-bold ${getPerformanceColor(agent.performance_rating)}`}>
                    {agent.success_rate}%
                  </p>
                  <p className={`text-xs ${getPerformanceColor(agent.performance_rating)}`}>
                    {agent.performance_rating}
                  </p>
                </div>
              </div>
            ))}
            {(!report.agent_stats?.agents || Object.keys(report.agent_stats.agents).length === 0) && (
              <p className="text-gray-500 text-center py-4">今日暂无任务数据</p>
            )}
          </div>
          <div className="mt-4 pt-4 border-t border-white/10 flex justify-between text-sm">
            <span className="text-gray-400">总任务数</span>
            <span className="font-bold">{report.agent_stats?.total_tasks || 0}</span>
          </div>
          <div className="flex justify-between text-sm mt-2">
            <span className="text-gray-400">整体成功率</span>
            <span className="font-bold text-cyber-green">{report.agent_stats?.overall_success_rate || 0}%</span>
          </div>
        </div>

        {/* 系统状态 */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-cyber-green" />
            系统状态
          </h2>
          <div className="flex items-center gap-3 p-4 bg-dark-purple/40 rounded-lg mb-4">
            <div className={`w-3 h-3 rounded-full ${
              report.system_health?.overall_status === 'healthy' ? 'bg-cyber-green' : 
              report.system_health?.overall_status === 'warning' ? 'bg-energy-orange' : 'bg-alert-red'
            }`} />
            <span className={`font-medium ${getStatusColor(report.system_health?.overall_status || '')}`}>
              {getStatusText(report.system_health?.overall_status || 'unknown')}
            </span>
          </div>

          {/* 亮点 */}
          {report.highlights && report.highlights.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-400 mb-2">今日亮点</h3>
              <div className="space-y-2">
                {report.highlights.map((highlight, index) => (
                  <div key={index} className="p-3 bg-cyber-green/10 border border-cyber-green/30 rounded-lg">
                    <p className="font-medium text-cyber-green">{highlight.title}</p>
                    <p className="text-gray-400 text-sm">{highlight.detail}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 问题 */}
          {report.issues && report.issues.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-400 mb-2">发现问题</h3>
              <div className="space-y-2">
                {report.issues.map((issue, index) => (
                  <div key={index} className={`p-3 border-l-4 rounded-lg ${getSeverityColor(issue.severity)}`}>
                    <p className="font-medium">{issue.title}</p>
                    <p className="text-gray-400 text-sm">{issue.detail}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 改进建议 */}
      {report.recommendations && report.recommendations.length > 0 && (
        <div className="glass-card p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-energy-orange" />
            改进建议
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {report.recommendations.map((rec, index) => (
              <div key={index} className="p-4 bg-dark-purple/40 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-0.5 rounded text-xs ${getPriorityColor(rec.priority)}`}>
                    {rec.priority === 'high' ? '高优先' : rec.priority === 'medium' ? '中优先' : '低优先'}
                  </span>
                </div>
                <p className="font-medium mb-1">{rec.action}</p>
                <p className="text-gray-400 text-sm">{rec.detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 业务数据详情 */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-bold mb-4">业务数据详情</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-dark-purple/40 rounded-lg">
            <p className="text-gray-400 text-sm mb-1">线索总数</p>
            <p className="text-2xl font-bold">{report.business_metrics?.leads?.total || 0}</p>
            <p className="text-cyber-green text-sm">+{report.business_metrics?.leads?.new_today || 0} 今日</p>
          </div>
          <div className="p-4 bg-dark-purple/40 rounded-lg">
            <p className="text-gray-400 text-sm mb-1">优质线索</p>
            <p className="text-2xl font-bold">{report.business_metrics?.leads?.quality_leads_today || 0}</p>
            <p className="text-gray-500 text-sm">质量分≥60</p>
          </div>
          <div className="p-4 bg-dark-purple/40 rounded-lg">
            <p className="text-gray-400 text-sm mb-1">客户总数</p>
            <p className="text-2xl font-bold">{report.business_metrics?.customers?.total || 0}</p>
            <p className="text-cyber-green text-sm">+{report.business_metrics?.customers?.new_today || 0} 今日</p>
          </div>
          <div className="p-4 bg-dark-purple/40 rounded-lg">
            <p className="text-gray-400 text-sm mb-1">独立对话客户</p>
            <p className="text-2xl font-bold">{report.business_metrics?.conversations?.unique_customers || 0}</p>
            <p className="text-gray-500 text-sm">今日互动</p>
          </div>
        </div>
      </div>
    </div>
  )
}
