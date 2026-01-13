'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Users, 
  MessageSquare, 
  Video, 
  TrendingUp,
  Bot,
  Bell,
  Settings,
  ChevronRight
} from 'lucide-react'
import Link from 'next/link'

// 动画配置
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
}

// 统计卡片组件
function StatCard({ 
  title, 
  value, 
  change, 
  icon: Icon,
  color = 'cyber-blue'
}: {
  title: string
  value: string | number
  change?: string
  icon: any
  color?: string
}) {
  return (
    <motion.div 
      variants={itemVariants}
      className="glass-card-hover p-6"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-gray-400 text-sm mb-1">{title}</p>
          <p className={`text-3xl font-bold font-number text-${color}`}>{value}</p>
          {change && (
            <p className="text-cyber-green text-sm mt-1">{change}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg bg-${color}/10`}>
          <Icon className={`w-6 h-6 text-${color}`} />
        </div>
      </div>
    </motion.div>
  )
}

// AI员工卡片组件
function AgentCard({ 
  name, 
  role, 
  status, 
  tasksToday 
}: {
  name: string
  role: string
  status: 'online' | 'busy' | 'offline'
  tasksToday: number
}) {
  const statusConfig = {
    online: { label: '在线', class: 'badge-online', glow: 'shadow-cyber' },
    busy: { label: '忙碌', class: 'badge-busy', glow: 'shadow-[0_0_15px_rgba(255,107,53,0.3)]' },
    offline: { label: '离线', class: 'badge-offline', glow: '' }
  }
  
  const config = statusConfig[status]
  
  return (
    <motion.div 
      variants={itemVariants}
      whileHover={{ scale: 1.02 }}
      className={`glass-card p-4 cursor-pointer transition-all ${config.glow}`}
    >
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center text-lg font-bold">
          {name[0]}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium">{name}</span>
            <span className={config.class}>{config.label}</span>
          </div>
          <p className="text-gray-400 text-sm">{role}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-number font-bold text-cyber-blue">{tasksToday}</p>
          <p className="text-gray-500 text-xs">今日任务</p>
        </div>
      </div>
    </motion.div>
  )
}

// 活动项组件
function ActivityItem({ 
  agent, 
  action, 
  time,
  highlight = false
}: {
  agent: string
  action: string
  time: string
  highlight?: boolean
}) {
  return (
    <motion.div 
      variants={itemVariants}
      className={`flex items-center gap-3 p-3 rounded-lg ${
        highlight ? 'bg-cyber-green/10 border border-cyber-green/30' : 'hover:bg-white/5'
      } transition-colors`}
    >
      <div className={`w-2 h-2 rounded-full ${highlight ? 'bg-cyber-green animate-pulse' : 'bg-gray-500'}`} />
      <span className="text-cyber-blue font-medium">[{agent}]</span>
      <span className="flex-1 text-gray-300 truncate">{action}</span>
      <span className="text-gray-500 text-sm">{time}</span>
    </motion.div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState({
    newCustomers: 0,
    highIntent: 0,
    conversations: 0,
    videos: 0,
    processing: 0
  })
  
  const [agents, setAgents] = useState([
    { name: '小调', role: '调度主管', status: 'online' as const, tasksToday: 0 },
    { name: '小销', role: '销售客服', status: 'online' as const, tasksToday: 0 },
    { name: '小析', role: '客户分析', status: 'online' as const, tasksToday: 0 },
    { name: '小文', role: '文案策划', status: 'online' as const, tasksToday: 0 },
    { name: '小视', role: '视频创作', status: 'online' as const, tasksToday: 0 },
    { name: '小跟', role: '跟进专员', status: 'online' as const, tasksToday: 0 },
  ])
  
  const [activities, setActivities] = useState<Array<{agent: string; action: string; time: string; highlight: boolean}>>([])
  const [loading, setLoading] = useState(true)
  
  // 获取真实数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 获取统计数据
        const statsRes = await fetch('/api/dashboard/stats')
        if (statsRes.ok) {
          const statsData = await statsRes.json()
          setStats({
            newCustomers: statsData.today?.new_customers || 0,
            highIntent: statsData.today?.high_intent_customers || 0,
            conversations: statsData.today?.conversations || 0,
            videos: statsData.today?.videos_generated || 0,
            processing: statsData.today?.processing_tasks || 0
          })
        }
        
        // 获取AI团队状态
        const teamRes = await fetch('/api/dashboard/team-status')
        if (teamRes.ok) {
          const teamData = await teamRes.json()
          if (teamData.agents && teamData.agents.length > 0) {
            const agentMap: Record<string, any> = {}
            teamData.agents.forEach((a: any) => {
              agentMap[a.name] = a
            })
            setAgents(prev => prev.map(agent => ({
              ...agent,
              status: agentMap[agent.name]?.status || 'online',
              tasksToday: agentMap[agent.name]?.tasks_today || 0
            })))
          }
        }
        
        // 获取最近活动
        const activitiesRes = await fetch('/api/dashboard/recent-activities')
        if (activitiesRes.ok) {
          const activitiesData = await activitiesRes.json()
          if (activitiesData.activities && activitiesData.activities.length > 0) {
            setActivities(activitiesData.activities.map((a: any, i: number) => ({
              agent: a.agent || '系统',
              action: a.content_preview || a.action || '活动记录',
              time: formatTime(a.timestamp),
              highlight: i === 0
            })))
          } else {
            setActivities([{ agent: '系统', action: '暂无活动记录', time: '刚刚', highlight: false }])
          }
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
    // 每30秒刷新一次
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])
  
  // 格式化时间
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    return `${Math.floor(diff / 86400)}天前`
  }
  
  return (
    <div className="min-h-screen p-6">
      {/* 顶部导航 */}
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-tech font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
            AI获客控制中心
          </h1>
          <p className="text-gray-400 mt-1">物流行业智能获客系统</p>
        </div>
        <div className="flex items-center gap-4">
          <button className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
            <Bell className="w-5 h-5 text-gray-400" />
          </button>
          <button className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
            <Settings className="w-5 h-5 text-gray-400" />
          </button>
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center font-bold">
            A
          </div>
        </div>
      </header>
      
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="space-y-6"
      >
        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            title="今日新客户" 
            value={stats.newCustomers}
            change="+15%"
            icon={Users}
            color="cyber-blue"
          />
          <StatCard 
            title="高意向客户" 
            value={stats.highIntent}
            change="+3 新增"
            icon={TrendingUp}
            color="cyber-green"
          />
          <StatCard 
            title="对话总数" 
            value={stats.conversations}
            icon={MessageSquare}
            color="neon-purple"
          />
          <StatCard 
            title="视频生成" 
            value={stats.videos}
            change="2 处理中"
            icon={Video}
            color="energy-orange"
          />
        </div>
        
        {/* 主内容区 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* AI团队状态 */}
          <motion.div variants={itemVariants} className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Bot className="w-5 h-5 text-cyber-blue" />
                AI员工团队
              </h2>
              <Link 
                href="/team" 
                className="text-cyber-blue hover:text-cyber-blue/80 flex items-center gap-1 text-sm"
              >
                查看详情 <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {agents.map((agent) => (
                <AgentCard key={agent.name} {...agent} />
              ))}
            </div>
          </motion.div>
          
          {/* 实时活动 */}
          <motion.div variants={itemVariants}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">实时动态</h2>
              <span className="text-gray-500 text-sm">自动刷新</span>
            </div>
            <div className="glass-card p-4 space-y-2">
              {activities.map((activity, index) => (
                <ActivityItem key={index} {...activity} />
              ))}
            </div>
          </motion.div>
        </div>
        
        {/* 快捷操作 */}
        <motion.div variants={itemVariants}>
          <h2 className="text-xl font-bold mb-4">快捷操作</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Link href="/videos/create" className="btn-cyber text-center py-4">
              <Video className="w-5 h-5 mx-auto mb-2" />
              生成视频
            </Link>
            <Link href="/customers" className="btn-cyber text-center py-4">
              <Users className="w-5 h-5 mx-auto mb-2" />
              客户列表
            </Link>
            <Link href="/conversations" className="btn-cyber text-center py-4">
              <MessageSquare className="w-5 h-5 mx-auto mb-2" />
              对话记录
            </Link>
            <Link href="/team" className="btn-cyber text-center py-4">
              <Bot className="w-5 h-5 mx-auto mb-2" />
              AI团队
            </Link>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}
