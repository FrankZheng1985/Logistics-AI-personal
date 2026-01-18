'use client'

import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowLeft,
  Search,
  Globe,
  Brain,
  PenTool,
  CheckCircle,
  AlertCircle,
  Activity,
  Play,
  Pause,
  RefreshCw,
  Loader2,
  Eye,
  Clock,
  BarChart3,
  TrendingUp,
  Calendar,
  Filter
} from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'

// AI员工信息配置
const AGENT_INFO: Record<string, {
  name: string
  role: string
  description: string
  color: string
}> = {
  lead_hunter: {
    name: '小猎',
    role: '线索猎手',
    description: '负责从互联网搜索潜在客户线索，自动发现物流需求、货代询价等商机。',
    color: 'from-orange-500 to-red-500'
  },
  analyst: {
    name: '小析',
    role: '客户分析师',
    description: '负责分析客户意向、评估客户价值、生成客户画像、市场情报采集。',
    color: 'from-blue-500 to-cyan-500'
  },
  analyst2: {
    name: '小析2',
    role: '群聊情报员',
    description: '负责监控微信群消息，提取有价值信息，更新知识库。只监控不发言。',
    color: 'from-indigo-500 to-purple-500'
  },
  coordinator: {
    name: '小调',
    role: '调度主管',
    description: '负责任务分配、流程协调、异常处理，是整个AI团队的核心协调者。',
    color: 'from-purple-500 to-pink-500'
  },
  sales: {
    name: '小销',
    role: '销售客服',
    description: '负责首次接待客户、解答物流咨询、收集客户需求信息、促成成交。',
    color: 'from-green-500 to-emerald-500'
  },
  follow: {
    name: '小跟',
    role: '跟进专员',
    description: '负责老客户维护、意向客户跟进、促成客户转化、流失挽回。',
    color: 'from-teal-500 to-cyan-500'
  },
  copywriter: {
    name: '小文',
    role: '文案策划',
    description: '负责撰写广告文案、视频脚本、朋友圈文案等营销内容。',
    color: 'from-pink-500 to-rose-500'
  },
  video_creator: {
    name: '小视',
    role: '视频创作员',
    description: '负责生成物流广告视频、产品展示视频等视觉内容。',
    color: 'from-amber-500 to-orange-500'
  },
  asset_collector: {
    name: '小采',
    role: '素材采集员',
    description: '负责从小红书、抖音、Pexels等社交媒体和素材网站自动采集物流相关视频、图片和音频素材。',
    color: 'from-emerald-500 to-teal-500'
  },
  content_creator: {
    name: '小媒',
    role: '内容运营',
    description: '负责每日内容生成、多平台发布、效果追踪，自动生成抖音、小红书、公众号等营销内容。',
    color: 'from-rose-500 to-pink-500'
  }
}

interface LiveStep {
  id: string
  agent_type: string
  agent_name: string
  session_id: string | null
  step_type: string
  step_title: string
  step_content: string | null
  step_data: any
  status: string
  created_at: string
}

interface TaskSession {
  id: string
  agent_type: string
  agent_name: string
  task_type: string
  task_description: string | null
  status: string
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  result_summary: string | null
}

// 获取步骤图标
function getStepIcon(stepType: string) {
  switch (stepType) {
    case 'search': return <Search className="w-4 h-4" />
    case 'fetch': return <Globe className="w-4 h-4" />
    case 'think': return <Brain className="w-4 h-4" />
    case 'write': return <PenTool className="w-4 h-4" />
    case 'result': return <CheckCircle className="w-4 h-4" />
    case 'error': return <AlertCircle className="w-4 h-4" />
    case 'start': return <Play className="w-4 h-4" />
    case 'complete': return <CheckCircle className="w-4 h-4" />
    case 'info': return <Activity className="w-4 h-4" />
    default: return <Activity className="w-4 h-4" />
  }
}

// 获取步骤颜色
function getStepColor(stepType: string, status: string) {
  if (status === 'failed') return 'border-alert-red/30 bg-alert-red/5'
  switch (stepType) {
    case 'search': return 'border-cyber-blue/30 bg-cyber-blue/5'
    case 'fetch': return 'border-neon-purple/30 bg-neon-purple/5'
    case 'think': return 'border-energy-orange/30 bg-energy-orange/5'
    case 'write': return 'border-pink-500/30 bg-pink-500/5'
    case 'result': return 'border-cyber-green/30 bg-cyber-green/5'
    case 'error': return 'border-alert-red/30 bg-alert-red/5'
    case 'complete': return 'border-cyber-green/30 bg-cyber-green/5'
    default: return 'border-gray-500/30 bg-gray-500/5'
  }
}

// 获取图标颜色
function getIconColor(stepType: string, status: string) {
  if (status === 'failed') return 'text-alert-red'
  switch (stepType) {
    case 'search': return 'text-cyber-blue'
    case 'fetch': return 'text-neon-purple'
    case 'think': return 'text-energy-orange'
    case 'write': return 'text-pink-500'
    case 'result': return 'text-cyber-green'
    case 'error': return 'text-alert-red'
    case 'complete': return 'text-cyber-green'
    default: return 'text-gray-400'
  }
}

export default function AgentLivePage() {
  const params = useParams()
  const agentType = params.agentType as string
  
  const [steps, setSteps] = useState<LiveStep[]>([])
  const [sessions, setSessions] = useState<TaskSession[]>([])
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  
  const wsRef = useRef<WebSocket | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  
  const agentInfo = AGENT_INFO[agentType] || {
    name: '未知',
    role: '未知',
    description: '未知AI员工',
    color: 'from-gray-500 to-gray-600'
  }
  
  // 加载历史步骤
  const fetchSteps = async () => {
    try {
      const url = selectedSession 
        ? `/api/live/${agentType}/steps?limit=100&session_id=${selectedSession}`
        : `/api/live/${agentType}/steps?limit=100`
      
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        setSteps(data.steps || [])
      }
    } catch (error) {
      console.error('获取历史步骤失败:', error)
    } finally {
      setLoading(false)
    }
  }
  
  // 加载任务会话列表
  const fetchSessions = async () => {
    try {
      const res = await fetch(`/api/live/${agentType}/sessions?limit=20`)
      if (res.ok) {
        const data = await res.json()
        setSessions(data.sessions || [])
      }
    } catch (error) {
      console.error('获取任务会话失败:', error)
    }
  }
  
  useEffect(() => {
    fetchSteps()
    fetchSessions()
  }, [agentType, selectedSession])
  
  // WebSocket连接
  useEffect(() => {
    let isMounted = true
    let ws: WebSocket | null = null
    let pingInterval: NodeJS.Timeout | null = null
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws/agent-live/${agentType}`
    
    // 延迟连接，避免快速切换时的错误
    const connectTimeout = setTimeout(() => {
      if (!isMounted) return
      
      try {
        ws = new WebSocket(wsUrl)
        wsRef.current = ws
        
        ws.onopen = () => {
          if (!isMounted) {
            ws?.close()
            return
          }
          setConnected(true)
        }
        
        ws.onmessage = (event) => {
          if (!isMounted) return
          try {
            const step = JSON.parse(event.data)
            if (step.type === 'connected' || step.type === 'pong') return
            
            // 如果选中了特定会话，只显示该会话的步骤
            if (selectedSession && step.session_id !== selectedSession) return
            
            setSteps(prev => [...prev, step])
            
            // 如果是任务开始或结束，刷新会话列表
            if (step.step_type === 'start' || step.step_type === 'complete' || step.step_type === 'error') {
              fetchSessions()
            }
          } catch {
            // 忽略解析错误
          }
        }
        
        ws.onclose = () => {
          if (isMounted) setConnected(false)
        }
        
        ws.onerror = () => {
          // 静默处理错误
        }
        
        // 心跳
        pingInterval = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 30000)
      } catch {
        // 忽略WebSocket创建错误
      }
    }, 300)
    
    return () => {
      isMounted = false
      clearTimeout(connectTimeout)
      if (pingInterval) clearInterval(pingInterval)
      // 只在连接已建立时关闭，避免"closed before established"警告
      if (ws) {
        try {
          if (ws.readyState === WebSocket.OPEN) {
            ws.close(1000, 'Component unmounted')
          }
        } catch {
          // 忽略关闭错误
        }
      }
    }
  }, [agentType, selectedSession])
  
  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [steps, autoScroll])
  
  const formatTime = (isoString: string | null) => {
    if (!isoString) return '-'
    const date = new Date(isoString)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
  
  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return '-'
    const date = new Date(isoString)
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
  
  const formatDuration = (ms: number | null) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}min`
  }
  
  // 统计数据
  const todaySteps = steps.filter(s => {
    const stepDate = new Date(s.created_at).toDateString()
    const today = new Date().toDateString()
    return stepDate === today
  })
  
  const stepTypeCount = steps.reduce((acc, step) => {
    acc[step.step_type] = (acc[step.step_type] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  
  return (
    <div className="min-h-screen p-6">
      {/* 头部 */}
      <header className="flex items-center gap-4 mb-8">
        <Link href="/team" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-4 flex-1">
          <div className={`w-16 h-16 rounded-full bg-gradient-to-br ${agentInfo.color} flex items-center justify-center text-2xl font-bold shadow-lg`}>
            {agentInfo.name}
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
                {agentInfo.name} - {agentInfo.role}
              </span>
              <span className="text-sm font-normal text-gray-400">实时工作直播</span>
              <span className={`w-3 h-3 rounded-full ${connected ? 'bg-cyber-green animate-pulse' : 'bg-gray-500'}`} />
            </h1>
            <p className="text-gray-400 text-sm">{agentInfo.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`p-2 glass-card transition-colors ${autoScroll ? 'border-cyber-green/50 text-cyber-green' : ''}`}
            title={autoScroll ? '关闭自动滚动' : '开启自动滚动'}
          >
            {autoScroll ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
          </button>
          <button
            onClick={() => {
              setLoading(true)
              fetchSteps()
              fetchSessions()
            }}
            className="p-2 glass-card hover:border-cyber-blue/50 transition-colors"
            title="刷新"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 左侧：任务会话列表 */}
        <div className="lg:col-span-1 space-y-4">
          <div className="glass-card p-4">
            <h2 className="font-bold mb-3 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-cyber-blue" />
              任务会话
            </h2>
            
            <button
              onClick={() => setSelectedSession(null)}
              className={`w-full text-left p-2 rounded-lg mb-2 transition-colors ${
                !selectedSession ? 'bg-cyber-blue/20 border border-cyber-blue/50' : 'hover:bg-white/5'
              }`}
            >
              <span className="text-sm">全部工作记录</span>
            </button>
            
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {sessions.map(session => (
                <button
                  key={session.id}
                  onClick={() => setSelectedSession(session.id)}
                  className={`w-full text-left p-2 rounded-lg transition-colors ${
                    selectedSession === session.id 
                      ? 'bg-cyber-blue/20 border border-cyber-blue/50' 
                      : 'hover:bg-white/5'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium truncate">{session.task_type}</span>
                    <span className={`w-2 h-2 rounded-full ${
                      session.status === 'completed' ? 'bg-cyber-green' :
                      session.status === 'failed' ? 'bg-alert-red' :
                      'bg-energy-orange animate-pulse'
                    }`} />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatDateTime(session.started_at)}
                    {session.duration_ms && ` • ${formatDuration(session.duration_ms)}`}
                  </div>
                </button>
              ))}
              
              {sessions.length === 0 && (
                <p className="text-gray-500 text-sm text-center py-4">暂无任务记录</p>
              )}
            </div>
          </div>
          
          {/* 统计卡片 */}
          <div className="glass-card p-4">
            <h2 className="font-bold mb-3 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-neon-purple" />
              工作统计
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-400 text-sm">总步骤数</span>
                <span className="font-number font-bold text-cyber-blue">{steps.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400 text-sm">今日步骤</span>
                <span className="font-number font-bold text-cyber-green">{todaySteps.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400 text-sm">搜索次数</span>
                <span className="font-number font-bold text-neon-purple">{stepTypeCount['search'] || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400 text-sm">分析次数</span>
                <span className="font-number font-bold text-energy-orange">{stepTypeCount['think'] || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400 text-sm">发现结果</span>
                <span className="font-number font-bold text-cyber-green">{stepTypeCount['result'] || 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* 右侧：实时工作流 */}
        <div className="lg:col-span-3">
          <div className="glass-card">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <h2 className="font-bold flex items-center gap-2">
                <Eye className="w-5 h-5 text-cyber-green" />
                实时工作流
                {connected && (
                  <span className="text-xs bg-cyber-green/20 text-cyber-green px-2 py-0.5 rounded-full">
                    直播中
                  </span>
                )}
              </h2>
              <span className="text-gray-500 text-sm">
                {selectedSession ? '查看特定会话' : '全部记录'} • 共 {steps.length} 条
              </span>
            </div>
            
            <div 
              ref={scrollRef}
              className="p-4 space-y-3 overflow-y-auto"
              style={{ height: 'calc(100vh - 350px)', minHeight: '400px' }}
            >
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="w-8 h-8 animate-spin text-cyber-blue" />
                </div>
              ) : steps.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <Eye className="w-16 h-16 mb-4 opacity-30" />
                  <p className="text-lg">等待工作开始...</p>
                  <p className="text-sm mt-2">当员工开始工作时，这里会实时显示工作过程</p>
                </div>
              ) : (
                steps.map((step, index) => (
                  <motion.div
                    key={step.id || index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`p-4 rounded-lg border ${getStepColor(step.step_type, step.status)}`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`mt-1 p-2 rounded-lg bg-white/5 ${getIconColor(step.step_type, step.status)}`}>
                        {step.status === 'running' ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          getStepIcon(step.step_type)
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="font-medium">{step.step_title}</p>
                          <span className="text-xs text-gray-500 whitespace-nowrap ml-2">
                            {formatTime(step.created_at)}
                          </span>
                        </div>
                        {step.step_content && (
                          <p className="text-sm text-gray-400 mt-1">{step.step_content}</p>
                        )}
                        {step.step_data && (
                          <div className="mt-2 p-2 bg-white/5 rounded text-xs text-gray-500 font-mono overflow-x-auto">
                            {typeof step.step_data === 'string' 
                              ? step.step_data 
                              : JSON.stringify(step.step_data, null, 2)
                            }
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
