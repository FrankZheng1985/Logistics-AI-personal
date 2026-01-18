'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowLeft,
  Play,
  Pause,
  RefreshCw,
  BarChart3,
  Clock,
  CheckCircle,
  XCircle,
  Activity,
  Calendar,
  TrendingUp,
  Settings,
  Loader2,
  AlertCircle
} from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'

// AI员工信息配置
const AGENT_INFO: Record<string, {
  name: string
  role: string
  description: string
  color: string
  tasks: string[]
}> = {
  lead_hunter: {
    name: '小猎',
    role: '线索猎手',
    description: '负责从互联网搜索潜在客户线索，自动发现物流需求、货代询价等商机。',
    color: 'from-orange-500 to-red-500',
    tasks: ['线索搜索', '内容分析', '联系方式提取', '质量评分']
  },
  analyst: {
    name: '小析',
    role: '客户分析师',
    description: '负责分析客户意向、评估客户价值、生成客户画像、市场情报采集。',
    color: 'from-blue-500 to-cyan-500',
    tasks: ['意向分析', '客户画像', '市场情报', '数据报表']
  },
  analyst2: {
    name: '小析2',
    role: '群聊情报员',
    description: '负责监控微信群消息，提取有价值信息，更新知识库。只监控不发言。',
    color: 'from-indigo-500 to-purple-500',
    tasks: ['群消息监控', '信息提取', '知识库更新', '线索发现']
  },
  coordinator: {
    name: '小调',
    role: '调度主管',
    description: '负责任务分配、流程协调、异常处理，是整个AI团队的核心协调者。',
    color: 'from-purple-500 to-pink-500',
    tasks: ['任务分配', '优先级调度', '负载均衡', '异常处理']
  },
  sales: {
    name: '小销',
    role: '销售客服',
    description: '负责首次接待客户、解答物流咨询、收集客户需求信息、促成成交。',
    color: 'from-green-500 to-emerald-500',
    tasks: ['客户接待', '需求收集', '报价咨询', '成交促进']
  },
  follow: {
    name: '小跟',
    role: '跟进专员',
    description: '负责老客户维护、意向客户跟进、促成客户转化、流失挽回。',
    color: 'from-teal-500 to-cyan-500',
    tasks: ['日常跟进', '客户维护', '复购提醒', '流失挽回']
  },
  copywriter: {
    name: '小文',
    role: '文案策划',
    description: '负责撰写广告文案、视频脚本、朋友圈文案等营销内容。',
    color: 'from-pink-500 to-rose-500',
    tasks: ['视频脚本', '朋友圈文案', '广告文案', '内容发布']
  },
  video_creator: {
    name: '小视',
    role: '视频创作员',
    description: '负责生成物流广告视频、产品展示视频等视觉内容。',
    color: 'from-amber-500 to-orange-500',
    tasks: ['视频生成', '脚本配合', '画面优化', '视频发布']
  },
  asset_collector: {
    name: '小采',
    role: '素材采集员',
    description: '负责从小红书、抖音、Pexels等社交媒体和素材网站自动采集物流相关视频、图片和音频素材。',
    color: 'from-emerald-500 to-teal-500',
    tasks: ['素材搜索', '视频采集', '图片采集', '素材入库']
  },
  content_creator: {
    name: '小媒',
    role: '内容运营',
    description: '负责每日内容生成、多平台发布、效果追踪，自动生成抖音、小红书、公众号等营销内容。',
    color: 'from-rose-500 to-pink-500',
    tasks: ['每日内容生成', '多平台发布', '内容规划', '效果分析']
  },
  eu_customs_monitor: {
    name: '小欧间谍',
    role: '欧洲海关监控员',
    description: '负责每天监控欧洲海关新闻，关注反倾销、关税调整、进口政策等，发现重要新闻立即通知。',
    color: 'from-blue-600 to-indigo-600',
    tasks: ['欧洲海关新闻采集', '反倾销政策监控', '关税调整追踪', '企业微信通知']
  }
}

interface WorkLog {
  id: string
  task_type: string
  status: 'success' | 'failed' | 'running'
  started_at: string
  completed_at: string | null
  duration_ms: number | null
  input_data?: any
  output_data?: any
  error_message?: string
  result_summary?: string  // 任务执行内容摘要
}

interface AgentStats {
  tasks_today: number
  tasks_total: number
  success_rate: number
  avg_duration_ms: number
  status: string
  last_active: string | null
}

export default function AgentDetailPage() {
  const params = useParams()
  const agentType = params.agentType as string
  
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [workLogs, setWorkLogs] = useState<WorkLog[]>([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  
  const agentInfo = AGENT_INFO[agentType] || {
    name: '未知',
    role: '未知',
    description: '未知AI员工',
    color: 'from-gray-500 to-gray-600',
    tasks: []
  }

  const fetchData = async () => {
    try {
      // 获取员工统计
      const statsRes = await fetch(`/api/agents/${agentType}`)
      if (statsRes.ok) {
        const data = await statsRes.json()
        setStats({
          tasks_today: data.tasks_today || 0,
          tasks_total: data.total_tasks || 0,
          success_rate: data.success_rate || 100,
          avg_duration_ms: data.avg_task_duration_ms || 0,
          status: data.status || 'online',
          last_active: data.last_active_at
        })
      }
      
      // 获取实时工作步骤
      const stepsRes = await fetch(`/api/live/${agentType}/steps?limit=20`)
      if (stepsRes.ok) {
        const data = await stepsRes.json()
        // 转换格式以适配WorkLog接口
        const logs = (data.steps || []).map((step: any) => ({
          id: step.id,
          task_type: step.step_type,
          status: step.status === 'completed' ? 'success' : step.status === 'failed' ? 'failed' : 'running',
          started_at: step.created_at,
          completed_at: step.status === 'completed' ? step.created_at : null,
          duration_ms: step.step_data?.duration_ms || null,
          result_summary: step.step_title + (step.step_content ? `: ${step.step_content}` : '')
        }))
        setWorkLogs(logs)
      }
      
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [agentType])

  const handleTriggerTask = async (taskType: string) => {
    setTriggering(true)
    try {
      // 触发任务
      const res = await fetch(`/api/agents/${agentType}/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_type: taskType })
      })
      
      if (res.ok) {
        alert(`已触发 ${taskType} 任务`)
        fetchData()
      } else {
        alert('触发失败')
      }
    } catch (error) {
      console.error('触发任务失败:', error)
      alert('触发失败')
    } finally {
      setTriggering(false)
    }
  }

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}min`
  }

  const formatTime = (isoString: string | null) => {
    if (!isoString) return '-'
    const date = new Date(isoString)
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // 解析日志内容，提取类型和内容
  const parseLogContent = (summary: string) => {
    // 检测不同类型的日志
    if (summary.includes('🚨') || summary.includes('发现重要新闻')) {
      const content = summary.replace(/🚨\s*发现重要新闻!?:?\s*/g, '').trim()
      return { type: 'important', label: '重要新闻', content, icon: '🚨' }
    }
    if (summary.includes('正在访问网页') || summary.includes('https://') || summary.includes('http://')) {
      const urlMatch = summary.match(/(https?:\/\/[^\s]+)/)
      const url = urlMatch ? urlMatch[1] : ''
      const domain = url ? new URL(url).hostname.replace('www.', '') : ''
      return { type: 'visit', label: '访问网页', content: domain || url, icon: '🔗' }
    }
    if (summary.includes('AI正在分析') || summary.includes('分析')) {
      const content = summary.replace(/AI正在分析\.+:?\s*/g, '').trim()
      return { type: 'analyze', label: '内容分析', content, icon: '🔍' }
    }
    if (summary.includes('搜索') || summary.includes('查询')) {
      return { type: 'search', label: '搜索', content: summary, icon: '🔎' }
    }
    if (summary.includes('保存') || summary.includes('存储')) {
      return { type: 'save', label: '数据存储', content: summary, icon: '💾' }
    }
    if (summary.includes('通知') || summary.includes('企业微信')) {
      return { type: 'notify', label: '发送通知', content: summary, icon: '📢' }
    }
    // 默认类型
    return { type: 'default', label: '执行', content: summary, icon: '⚡' }
  }

  // 截断文本
  const truncateText = (text: string, maxLength: number = 50) => {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.slice(0, maxLength) + '...'
  }

  return (
    <div className="min-h-screen p-6">
      {/* 头部 */}
      <header className="flex items-center gap-4 mb-8">
        <Link href="/team" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-4">
          <div className={`w-16 h-16 rounded-full bg-gradient-to-br ${agentInfo.color} flex items-center justify-center text-2xl font-bold shadow-lg`}>
            {agentInfo.name}
          </div>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
                {agentInfo.name} - {agentInfo.role}
              </span>
              <span className={`px-2 py-1 rounded-full text-xs ${
                stats?.status === 'online' ? 'bg-cyber-green/20 text-cyber-green' :
                stats?.status === 'busy' ? 'bg-energy-orange/20 text-energy-orange' :
                'bg-gray-500/20 text-gray-400'
              }`}>
                {stats?.status === 'online' ? '在线' : stats?.status === 'busy' ? '忙碌' : '离线'}
              </span>
            </h1>
            <p className="text-gray-400 text-sm">{agentInfo.description}</p>
          </div>
        </div>
      </header>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-cyber-blue" />
        </div>
      ) : (
        <>
          {/* 统计卡片 */}
          <div className="grid grid-cols-4 gap-4 mb-8">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-6 text-center"
            >
              <CheckCircle className="w-8 h-8 text-cyber-blue mx-auto mb-2" />
              <p className="text-3xl font-number font-bold text-cyber-blue">
                {stats?.tasks_today || 0}
              </p>
              <p className="text-gray-500 text-sm">今日任务</p>
            </motion.div>
            
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-card p-6 text-center"
            >
              <BarChart3 className="w-8 h-8 text-neon-purple mx-auto mb-2" />
              <p className="text-3xl font-number font-bold text-neon-purple">
                {stats?.tasks_total || 0}
              </p>
              <p className="text-gray-500 text-sm">累计任务</p>
            </motion.div>
            
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="glass-card p-6 text-center"
            >
              <TrendingUp className="w-8 h-8 text-cyber-green mx-auto mb-2" />
              <p className="text-3xl font-number font-bold text-cyber-green">
                {stats?.success_rate || 100}%
              </p>
              <p className="text-gray-500 text-sm">成功率</p>
            </motion.div>
            
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="glass-card p-6 text-center"
            >
              <Clock className="w-8 h-8 text-energy-orange mx-auto mb-2" />
              <p className="text-3xl font-number font-bold text-energy-orange">
                {formatDuration(stats?.avg_duration_ms || 0)}
              </p>
              <p className="text-gray-500 text-sm">平均耗时</p>
            </motion.div>
          </div>

          {/* 快捷操作 */}
          <div className="glass-card p-6 mb-8">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Play className="w-5 h-5 text-cyber-blue" />
              手动触发任务
            </h2>
            <div className="flex flex-wrap gap-3">
              {agentInfo.tasks.map((task, index) => (
                <motion.button
                  key={task}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => handleTriggerTask(task)}
                  disabled={triggering}
                  className="px-4 py-2 glass-card hover:border-cyber-blue/50 hover:bg-cyber-blue/10 transition-all flex items-center gap-2 disabled:opacity-50"
                >
                  {triggering ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  {task}
                </motion.button>
              ))}
              <button 
                onClick={() => fetchData()}
                className="px-4 py-2 glass-card hover:border-neon-purple/50 transition-colors flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                刷新数据
              </button>
            </div>
          </div>

          {/* 工作日志 */}
          <div className="glass-card p-6">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-neon-purple" />
              工作日志
              <span className="text-xs text-gray-500 font-normal ml-2">
                共 {workLogs.length} 条记录
              </span>
            </h2>
            
            <div className="space-y-2">
              {workLogs.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Calendar className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>暂无工作日志</p>
                </div>
              ) : (
                workLogs.map((log, index) => {
                  const parsed = parseLogContent(log.result_summary || log.task_type)
                  
                  return (
                    <motion.div
                      key={log.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className={`p-3 rounded-lg border transition-all hover:scale-[1.01] ${
                        parsed.type === 'important' 
                          ? 'bg-amber-500/10 border-amber-500/30 hover:border-amber-500/50' 
                          : log.status === 'success' 
                            ? 'bg-cyber-green/5 border-cyber-green/20 hover:border-cyber-green/40' 
                            : log.status === 'failed' 
                              ? 'bg-alert-red/5 border-alert-red/20 hover:border-alert-red/40' 
                              : 'bg-cyber-blue/5 border-cyber-blue/20 hover:border-cyber-blue/40'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {/* 左侧：类型图标 */}
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          parsed.type === 'important' ? 'bg-amber-500/20' :
                          parsed.type === 'visit' ? 'bg-blue-500/20' :
                          parsed.type === 'analyze' ? 'bg-purple-500/20' :
                          parsed.type === 'notify' ? 'bg-green-500/20' :
                          'bg-gray-500/20'
                        }`}>
                          <span className="text-base">{parsed.icon}</span>
                        </div>
                        
                        {/* 中间：内容 */}
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                              parsed.type === 'important' ? 'bg-amber-500/30 text-amber-300' :
                              parsed.type === 'visit' ? 'bg-blue-500/30 text-blue-300' :
                              parsed.type === 'analyze' ? 'bg-purple-500/30 text-purple-300' :
                              parsed.type === 'notify' ? 'bg-green-500/30 text-green-300' :
                              'bg-gray-500/30 text-gray-300'
                            }`}>
                              {parsed.label}
                            </span>
                            <span className="text-xs text-gray-500">
                              {formatTime(log.started_at)}
                            </span>
                          </div>
                          <p className={`text-sm mt-1 truncate ${
                            parsed.type === 'important' ? 'text-amber-200 font-medium' : 'text-gray-300'
                          }`} title={parsed.content}>
                            {truncateText(parsed.content, 60)}
                          </p>
                        </div>
                        
                        {/* 右侧：状态 */}
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {log.status === 'success' ? (
                            <CheckCircle className="w-4 h-4 text-cyber-green" />
                          ) : log.status === 'failed' ? (
                            <XCircle className="w-4 h-4 text-alert-red" />
                          ) : (
                            <Loader2 className="w-4 h-4 text-cyber-blue animate-spin" />
                          )}
                          <span className={`text-xs ${
                            log.status === 'success' ? 'text-cyber-green' :
                            log.status === 'failed' ? 'text-alert-red' :
                            'text-cyber-blue'
                          }`}>
                            {log.status === 'success' ? '完成' : log.status === 'failed' ? '失败' : '进行中'}
                          </span>
                        </div>
                      </div>
                      
                      {/* 错误信息 */}
                      {log.error_message && (
                        <div className="mt-2 ml-11 p-2 bg-alert-red/10 rounded text-xs text-alert-red flex items-start gap-2">
                          <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          <span className="truncate">{log.error_message}</span>
                        </div>
                      )}
                    </motion.div>
                  )
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
