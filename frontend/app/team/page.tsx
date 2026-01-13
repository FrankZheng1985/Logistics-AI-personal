'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowLeft,
  Settings,
  BarChart3,
  MessageSquare,
  CheckCircle,
  Clock,
  Zap
} from 'lucide-react'
import Link from 'next/link'

// AI员工详细卡片
function AgentDetailCard({ agent }: { agent: any }) {
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
    >
      {/* 头部 */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center text-2xl font-bold">
              {agent.name}
            </div>
            <div className={`absolute -bottom-1 -right-1 w-5 h-5 rounded-full ${statusColors[agent.status as keyof typeof statusColors]} border-2 border-deep-space`} />
          </div>
          <div>
            <h3 className="text-xl font-bold">{agent.name}</h3>
            <p className="text-gray-400">{agent.role}</p>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs ${
              agent.status === 'online' ? 'bg-cyber-green/20 text-cyber-green' :
              agent.status === 'busy' ? 'bg-energy-orange/20 text-energy-orange' :
              'bg-gray-500/20 text-gray-400'
            }`}>
              {statusLabels[agent.status as keyof typeof statusLabels]}
            </span>
          </div>
        </div>
        <button className="p-2 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10 rounded-lg">
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
function TeamStats({ agents }: { agents: any[] }) {
  const onlineCount = agents.filter(a => a.status === 'online').length
  const busyCount = agents.filter(a => a.status === 'busy').length
  const totalTasksToday = agents.reduce((sum, a) => sum + a.tasksToday, 0)
  
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
        <p className="text-3xl font-number font-bold text-cyber-green">{onlineCount}</p>
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
        <p className="text-3xl font-number font-bold text-energy-orange">{busyCount}</p>
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
        <p className="text-3xl font-number font-bold text-cyber-blue">{totalTasksToday}</p>
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
        <p className="text-3xl font-number font-bold text-neon-purple">98%</p>
      </motion.div>
    </div>
  )
}

export default function TeamPage() {
  const [agents] = useState([
    { 
      name: '小调', 
      role: 'AI调度主管', 
      status: 'online',
      description: '负责任务分配、流程协调、异常处理，是整个AI团队的核心协调者。',
      tasksToday: 45,
      totalTasks: 12580,
      successRate: 99,
      currentTask: null
    },
    { 
      name: '小销', 
      role: '销售客服', 
      status: 'busy',
      description: '负责首次接待客户、解答物流咨询、收集客户需求信息。',
      tasksToday: 32,
      totalTasks: 8920,
      successRate: 97,
      currentTask: '正在与客户沟通...'
    },
    { 
      name: '小析', 
      role: '客户分析师', 
      status: 'online',
      description: '负责分析客户意向、评估客户价值、生成客户画像。',
      tasksToday: 28,
      totalTasks: 7650,
      successRate: 98,
      currentTask: null
    },
    { 
      name: '小文', 
      role: '文案策划', 
      status: 'online',
      description: '负责撰写广告文案、视频脚本、朋友圈文案等营销内容。',
      tasksToday: 15,
      totalTasks: 4320,
      successRate: 96,
      currentTask: null
    },
    { 
      name: '小视', 
      role: '视频创作员', 
      status: 'busy',
      description: '负责生成物流广告视频、产品展示视频等视觉内容。',
      tasksToday: 8,
      totalTasks: 1250,
      successRate: 94,
      currentTask: '正在生成视频...'
    },
    { 
      name: '小跟', 
      role: '跟进专员', 
      status: 'online',
      description: '负责老客户维护、意向客户跟进、促成客户转化。',
      tasksToday: 19,
      totalTasks: 5680,
      successRate: 95,
      currentTask: null
    },
  ])
  
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
            <span className="text-sm font-normal text-gray-400">6 名员工</span>
          </h1>
          <p className="text-gray-400 text-sm">管理和监控AI员工工作状态</p>
        </div>
      </header>
      
      {/* 团队统计 */}
      <TeamStats agents={agents} />
      
      {/* AI员工卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent, index) => (
          <motion.div
            key={agent.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <AgentDetailCard agent={agent} />
          </motion.div>
        ))}
      </div>
    </div>
  )
}
