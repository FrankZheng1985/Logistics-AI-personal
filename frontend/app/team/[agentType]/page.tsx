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
          tasks_today: data.tasks_completed_today || 0,
          tasks_total: data.tasks_completed_total || 0,
          success_rate: data.success_rate || 100,
          avg_duration_ms: data.avg_task_duration_ms || 0,
          status: data.status || 'online',
          last_active: data.last_active_at
        })
      }
      
      // 获取工作日志（模拟数据，实际需要API）
      // const logsRes = await fetch(`/api/agents/${agentType}/logs`)
      // if (logsRes.ok) {
      //   setWorkLogs(await logsRes.json())
      // }
      
      // 模拟工作日志数据
      setWorkLogs([
        {
          id: '1',
          task_type: agentInfo.tasks[0] || '任务',
          status: 'success',
          started_at: new Date(Date.now() - 3600000).toISOString(),
          completed_at: new Date(Date.now() - 3500000).toISOString(),
          duration_ms: 100000
        },
        {
          id: '2',
          task_type: agentInfo.tasks[1] || '任务',
          status: 'success',
          started_at: new Date(Date.now() - 7200000).toISOString(),
          completed_at: new Date(Date.now() - 7100000).toISOString(),
          duration_ms: 100000
        },
        {
          id: '3',
          task_type: agentInfo.tasks[0] || '任务',
          status: 'running',
          started_at: new Date().toISOString(),
          completed_at: null,
          duration_ms: null
        }
      ])
      
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
            </h2>
            
            <div className="space-y-3">
              {workLogs.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Calendar className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>暂无工作日志</p>
                </div>
              ) : (
                workLogs.map((log, index) => (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`p-4 rounded-lg border ${
                      log.status === 'success' ? 'bg-cyber-green/5 border-cyber-green/20' :
                      log.status === 'failed' ? 'bg-alert-red/5 border-alert-red/20' :
                      'bg-cyber-blue/5 border-cyber-blue/20'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {log.status === 'success' ? (
                          <CheckCircle className="w-5 h-5 text-cyber-green" />
                        ) : log.status === 'failed' ? (
                          <XCircle className="w-5 h-5 text-alert-red" />
                        ) : (
                          <Loader2 className="w-5 h-5 text-cyber-blue animate-spin" />
                        )}
                        <div>
                          <p className="font-medium">{log.task_type}</p>
                          <p className="text-sm text-gray-500">
                            {formatTime(log.started_at)}
                            {log.completed_at && ` → ${formatTime(log.completed_at)}`}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`px-2 py-1 rounded text-xs ${
                          log.status === 'success' ? 'bg-cyber-green/20 text-cyber-green' :
                          log.status === 'failed' ? 'bg-alert-red/20 text-alert-red' :
                          'bg-cyber-blue/20 text-cyber-blue'
                        }`}>
                          {log.status === 'success' ? '完成' : log.status === 'failed' ? '失败' : '进行中'}
                        </span>
                        {log.duration_ms && (
                          <p className="text-sm text-gray-500 mt-1">
                            耗时: {formatDuration(log.duration_ms)}
                          </p>
                        )}
                      </div>
                    </div>
                    {log.error_message && (
                      <div className="mt-2 p-2 bg-alert-red/10 rounded text-sm text-alert-red flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        {log.error_message}
                      </div>
                    )}
                  </motion.div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
