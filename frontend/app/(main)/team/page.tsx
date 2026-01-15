'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  ArrowLeft,
  Settings,
  BarChart3,
  MessageSquare,
  CheckCircle,
  Clock,
  Zap,
  Loader2,
  X,
  Power,
  Sliders,
  Activity,
  RefreshCw
} from 'lucide-react'
import Link from 'next/link'

interface Agent {
  name: string
  role: string
  status: 'online' | 'busy' | 'offline'
  description: string
  tasksToday: number
  totalTasks: number
  successRate: number
  currentTask: string | null
}

// AI员工配置弹窗
function AgentConfigModal({ 
  agent, 
  onClose,
  onToggleStatus,
  onRefreshStats
}: { 
  agent: Agent | null
  onClose: () => void
  onToggleStatus: (agentName: string, newStatus: 'online' | 'offline') => void
  onRefreshStats: () => void
}) {
  const [saving, setSaving] = useState(false)
  
  if (!agent) return null
  
  const handleToggleStatus = async () => {
    setSaving(true)
    const newStatus = agent.status === 'offline' ? 'online' : 'offline'
    await onToggleStatus(agent.name, newStatus)
    setSaving(false)
  }
  
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      onClick={onClose}
    >
      <motion.div 
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className="glass-card w-full max-w-lg mx-4"
        onClick={e => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center text-xl font-bold">
              {agent.name}
            </div>
            <div>
              <h2 className="text-lg font-bold">{agent.name} - {agent.role}</h2>
              <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs ${
                agent.status === 'online' ? 'bg-cyber-green/20 text-cyber-green' :
                agent.status === 'busy' ? 'bg-energy-orange/20 text-energy-orange' :
                'bg-gray-500/20 text-gray-400'
              }`}>
                {agent.status === 'online' ? '在线' : agent.status === 'busy' ? '忙碌' : '离线'}
              </span>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* 内容 */}
        <div className="p-6 space-y-6">
          {/* 描述 */}
          <div className="glass-card p-4">
            <h3 className="text-sm text-gray-400 mb-2">职责描述</h3>
            <p className="text-gray-200">{agent.description}</p>
          </div>
          
          {/* 统计 */}
          <div className="grid grid-cols-3 gap-4">
            <div className="glass-card p-4 text-center">
              <p className="text-2xl font-number font-bold text-cyber-blue">{agent.tasksToday}</p>
              <p className="text-gray-500 text-xs">今日任务</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-2xl font-number font-bold text-neon-purple">{agent.totalTasks}</p>
              <p className="text-gray-500 text-xs">累计任务</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-2xl font-number font-bold text-cyber-green">{agent.successRate}%</p>
              <p className="text-gray-500 text-xs">成功率</p>
            </div>
          </div>
          
          {/* 当前任务 */}
          {agent.currentTask && (
            <div className="glass-card p-4 bg-cyber-blue/10 border-cyber-blue/30">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyber-blue animate-pulse" />
                <span className="text-gray-400">当前任务：</span>
                <span className="text-cyber-blue">{agent.currentTask}</span>
              </div>
            </div>
          )}
          
          {/* 操作按钮 */}
          <div className="flex gap-3">
            <button 
              onClick={handleToggleStatus}
              disabled={saving || agent.status === 'busy'}
              className={`flex-1 py-3 glass-card transition-colors flex items-center justify-center gap-2 ${
                agent.status === 'offline' 
                  ? 'hover:border-cyber-green/50 hover:text-cyber-green' 
                  : 'hover:border-alert-red/50 hover:text-alert-red'
              } disabled:opacity-50`}
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Power className="w-4 h-4" />
              )}
              {agent.status === 'offline' ? '启用员工' : '禁用员工'}
            </button>
            <button 
              onClick={onRefreshStats}
              className="py-3 px-6 glass-card hover:border-cyber-blue/50 transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              刷新数据
            </button>
          </div>
          
          <p className="text-gray-500 text-xs text-center">
            💡 AI员工状态由系统自动管理，通常无需手动调整
          </p>
        </div>
      </motion.div>
    </motion.div>
  )
}

// AI员工详细卡片
function AgentDetailCard({ agent, onOpenConfig }: { agent: Agent; onOpenConfig: () => void }) {
  const statusColors = {
    online: 'bg-cyber-green',
    busy: 'bg-energy-orange',
    offline: 'bg-gray-500'
  }
  
  const statusLabels = {
    online: '在线',
    busy: '忙碌',
    offline: '离线'
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      className="glass-card p-6 cursor-pointer group"
      onClick={onOpenConfig}
    >
      {/* 头部 */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center text-2xl font-bold">
              {agent.name}
            </div>
            <div className={`absolute -bottom-1 -right-1 w-5 h-5 rounded-full ${statusColors[agent.status]} border-2 border-deep-space`} />
          </div>
          <div>
            <h3 className="text-xl font-bold">{agent.name}</h3>
            <p className="text-gray-400">{agent.role}</p>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs ${
              agent.status === 'online' ? 'bg-cyber-green/20 text-cyber-green' :
              agent.status === 'busy' ? 'bg-energy-orange/20 text-energy-orange' :
              'bg-gray-500/20 text-gray-400'
            }`}>
              {statusLabels[agent.status]}
            </span>
          </div>
        </div>
        <button 
          onClick={(e) => {
            e.stopPropagation()
            onOpenConfig()
          }}
          className="p-2 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10 rounded-lg"
        >
          <Settings className="w-5 h-5 text-gray-400" />
        </button>
      </div>
      
      {/* 描述 */}
      <p className="text-gray-400 text-sm mb-4">{agent.description}</p>
      
      {/* 统计 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center p-3 bg-white/5 rounded-lg">
          <p className="text-2xl font-number font-bold text-cyber-blue">{agent.tasksToday}</p>
          <p className="text-gray-500 text-xs">今日任务</p>
        </div>
        <div className="text-center p-3 bg-white/5 rounded-lg">
          <p className="text-2xl font-number font-bold text-neon-purple">{agent.totalTasks}</p>
          <p className="text-gray-500 text-xs">总任务</p>
        </div>
        <div className="text-center p-3 bg-white/5 rounded-lg">
          <p className="text-2xl font-number font-bold text-cyber-green">{agent.successRate}%</p>
          <p className="text-gray-500 text-xs">成功率</p>
        </div>
      </div>
      
      {/* 当前任务 */}
      {agent.currentTask && (
        <div className="mt-4 p-3 bg-cyber-blue/10 border border-cyber-blue/30 rounded-lg">
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-cyber-blue animate-pulse" />
            <span className="text-gray-300">当前任务：</span>
            <span className="text-cyber-blue">{agent.currentTask}</span>
          </div>
        </div>
      )}
    </motion.div>
  )
}

// 团队统计组件
function TeamStats({ agents, loading }: { agents: Agent[], loading: boolean }) {
  const onlineCount = agents.filter(a => a.status === 'online').length
  const busyCount = agents.filter(a => a.status === 'busy').length
  const totalTasksToday = agents.reduce((sum, a) => sum + a.tasksToday, 0)
  const avgSuccessRate = agents.length > 0 
    ? Math.round(agents.reduce((sum, a) => sum + a.successRate, 0) / agents.length)
    : 0
  
  return (
    <div className="grid grid-cols-4 gap-4 mb-8">
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-4 text-center"
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          <Zap className="w-5 h-5 text-cyber-green" />
          <span className="text-gray-400">在线员工</span>
        </div>
        {loading ? (
          <Loader2 className="w-8 h-8 animate-spin text-cyber-green mx-auto" />
        ) : (
          <p className="text-3xl font-number font-bold text-cyber-green">{onlineCount}</p>
        )}
      </motion.div>
      
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-card p-4 text-center"
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          <Clock className="w-5 h-5 text-energy-orange" />
          <span className="text-gray-400">忙碌员工</span>
        </div>
        {loading ? (
          <Loader2 className="w-8 h-8 animate-spin text-energy-orange mx-auto" />
        ) : (
          <p className="text-3xl font-number font-bold text-energy-orange">{busyCount}</p>
        )}
      </motion.div>
      
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-4 text-center"
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          <CheckCircle className="w-5 h-5 text-cyber-blue" />
          <span className="text-gray-400">今日任务</span>
        </div>
        {loading ? (
          <Loader2 className="w-8 h-8 animate-spin text-cyber-blue mx-auto" />
        ) : (
          <p className="text-3xl font-number font-bold text-cyber-blue">{totalTasksToday}</p>
        )}
      </motion.div>
      
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card p-4 text-center"
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          <BarChart3 className="w-5 h-5 text-neon-purple" />
          <span className="text-gray-400">平均成功率</span>
        </div>
        {loading ? (
          <Loader2 className="w-8 h-8 animate-spin text-neon-purple mx-auto" />
        ) : (
          <p className="text-3xl font-number font-bold text-neon-purple">{avgSuccessRate}%</p>
        )}
      </motion.div>
    </div>
  )
}

// AI员工的默认配置
const DEFAULT_AGENTS: Agent[] = [
  { 
    name: '小调', 
    role: 'AI调度主管', 
    status: 'online',
    description: '负责任务分配、流程协调、异常处理，是整个AI团队的核心协调者。',
    tasksToday: 0,
    totalTasks: 0,
    successRate: 100,
    currentTask: null
  },
  { 
    name: '小销', 
    role: '销售客服', 
    status: 'online',
    description: '负责首次接待客户、解答物流咨询、收集客户需求信息。',
    tasksToday: 0,
    totalTasks: 0,
    successRate: 100,
    currentTask: null
  },
  { 
    name: '小析', 
    role: '客户分析师', 
    status: 'online',
    description: '负责分析客户意向、评估客户价值、生成客户画像。',
    tasksToday: 0,
    totalTasks: 0,
    successRate: 100,
    currentTask: null
  },
  { 
    name: '小文', 
    role: '文案策划', 
    status: 'online',
    description: '负责撰写广告文案、视频脚本、朋友圈文案等营销内容。',
    tasksToday: 0,
    totalTasks: 0,
    successRate: 100,
    currentTask: null
  },
  { 
    name: '小视', 
    role: '视频创作员', 
    status: 'online',
    description: '负责生成物流广告视频、产品展示视频等视觉内容。',
    tasksToday: 0,
    totalTasks: 0,
    successRate: 100,
    currentTask: null
  },
  { 
    name: '小跟', 
    role: '跟进专员', 
    status: 'online',
    description: '负责老客户维护、意向客户跟进、促成客户转化。',
    tasksToday: 0,
    totalTasks: 0,
    successRate: 100,
    currentTask: null
  },
  { 
    name: '小猎', 
    role: '线索猎手', 
    status: 'online',
    description: '负责从互联网搜索潜在客户线索，自动发现物流需求、货代询价等商机。',
    tasksToday: 0,
    totalTasks: 0,
    successRate: 100,
    currentTask: null
  },
  { 
    name: '小采', 
    role: '素材采集员', 
    status: 'online',
    description: '负责从小红书、抖音、Pexels等平台自动采集物流相关视频、图片和音频素材。',
    tasksToday: 0,
    totalTasks: 0,
    successRate: 100,
    currentTask: null
  },
]

export default function TeamPage() {
  const [agents, setAgents] = useState<Agent[]>(DEFAULT_AGENTS)
  const [loading, setLoading] = useState(true)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  const fetchAgentData = async () => {
    try {
      const response = await fetch('/api/agents')
      
      if (response.ok) {
        const data = await response.json()
        
        if (data.agents && data.agents.length > 0) {
          const mappedAgents = data.agents.map((apiAgent: any) => {
            const defaultAgent = DEFAULT_AGENTS.find(a => a.name === apiAgent.name)
            
            return {
              name: apiAgent.name,
              role: defaultAgent?.role || apiAgent.type,
              status: apiAgent.status || 'online',
              description: defaultAgent?.description || apiAgent.description,
              tasksToday: apiAgent.tasks_today || 0,
              totalTasks: apiAgent.total_tasks || 0,
              successRate: apiAgent.success_rate || 100,
              currentTask: apiAgent.current_task_id ? '处理中...' : null
            }
          })
          setAgents(mappedAgents)
        } else {
          setAgents(DEFAULT_AGENTS)
        }
      } else {
        setAgents(DEFAULT_AGENTS)
      }
    } catch (error) {
      console.error('获取AI员工数据失败:', error)
      setAgents(DEFAULT_AGENTS)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setLoading(true)
    fetchAgentData()
    
    const interval = setInterval(fetchAgentData, 30000)
    return () => clearInterval(interval)
  }, [])
  
  const handleToggleStatus = async (agentName: string, newStatus: 'online' | 'offline') => {
    try {
      // 调用API更新状态
      const response = await fetch(`/api/agents/by-name/${encodeURIComponent(agentName)}/status?status=${newStatus}`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '更新失败')
      }
      
      // 本地更新状态
      setAgents(prev => prev.map(a => 
        a.name === agentName ? { ...a, status: newStatus } : a
      ))
      
      // 更新选中的agent
      if (selectedAgent?.name === agentName) {
        setSelectedAgent(prev => prev ? { ...prev, status: newStatus } : null)
      }
      
      alert(`${agentName} 状态已更新为: ${newStatus === 'online' ? '在线' : '离线'}`)
    } catch (error) {
      console.error('更新状态失败:', error)
      alert('更新失败，请重试')
    }
  }
  
  return (
    <div className="min-h-screen p-6">
      {/* 头部 */}
      <header className="flex items-center gap-4 mb-8">
        <Link href="/dashboard" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
              AI员工团队
            </span>
            <span className="text-sm font-normal text-gray-400">{agents.length} 名员工</span>
          </h1>
          <p className="text-gray-400 text-sm">管理和监控AI员工工作状态 • 点击员工卡片查看详情</p>
        </div>
      </header>
      
      {/* 团队统计 */}
      <TeamStats agents={agents} loading={loading} />
      
      {/* AI员工卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent, index) => (
          <motion.div
            key={agent.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <AgentDetailCard 
              agent={agent} 
              onOpenConfig={() => setSelectedAgent(agent)}
            />
          </motion.div>
        ))}
      </div>
      
      {/* 说明 */}
      <div className="mt-8 p-4 glass-card border-cyber-blue/30">
        <p className="text-gray-400 text-sm">
          💡 <strong className="text-cyber-blue">提示：</strong>
          AI员工的任务统计会随着企业微信对话自动更新。发送消息给企业微信AI客服，数据将实时反映在此页面。
        </p>
      </div>
      
      {/* AI员工配置弹窗 */}
      <AnimatePresence>
        {selectedAgent && (
          <AgentConfigModal 
            agent={selectedAgent}
            onClose={() => setSelectedAgent(null)}
            onToggleStatus={handleToggleStatus}
            onRefreshStats={() => {
              setLoading(true)
              fetchAgentData()
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
