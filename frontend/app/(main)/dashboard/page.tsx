'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Users, 
  MessageSquare, 
  Video, 
  TrendingUp,
  Bot,
  Bell,
  Settings,
  ChevronRight,
  X,
  Check
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

// 通知弹窗
function NotificationsModal({ 
  isOpen, 
  onClose,
  notifications,
  onMarkRead,
  onClearAll
}: { 
  isOpen: boolean
  onClose: () => void
  notifications: Array<{ id: string; title: string; content: string; time: string; read: boolean; action_url?: string }>
  onMarkRead: (id: string) => void
  onClearAll: () => void
}) {
  if (!isOpen) return null
  
  const handleNotificationClick = (notif: { id: string; action_url?: string; read: boolean }) => {
    onMarkRead(notif.id)
    // 如果有跳转链接，则跳转
    if (notif.action_url) {
      onClose()
      window.location.href = notif.action_url
    }
  }
  
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/60"
      onClick={onClose}
    >
      <motion.div 
        initial={{ scale: 0.95, y: -20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: -20 }}
        className="glass-card w-full max-w-md mx-4 max-h-[70vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-cyber-blue" />
            <h2 className="font-bold">通知中心</h2>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={onClearAll}
              className="text-xs text-gray-400 hover:text-cyber-blue transition-colors"
            >
              全部已读
            </button>
            <button 
              onClick={onClose}
              className="p-1 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        <div className="overflow-y-auto max-h-[50vh]">
          {notifications.length === 0 ? (
            <div className="p-8 text-center">
              <Bell className="w-10 h-10 text-gray-600 mx-auto mb-2" />
              <p className="text-gray-500">暂无通知</p>
            </div>
          ) : (
            notifications.map((notif) => (
              <div 
                key={notif.id}
                onClick={() => handleNotificationClick(notif)}
                className={`p-4 border-b border-white/5 cursor-pointer transition-colors hover:bg-white/5 ${
                  !notif.read ? 'bg-cyber-blue/5' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-2 h-2 mt-2 rounded-full ${notif.read ? 'bg-gray-600' : 'bg-cyber-blue animate-pulse'}`} />
                  <div className="flex-1">
                    <p className="font-medium text-sm">{notif.title}</p>
                    <p className="text-gray-400 text-xs mt-1 line-clamp-2">{notif.content}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <p className="text-gray-500 text-xs">{notif.time}</p>
                      {notif.action_url && (
                        <span className="text-cyber-blue text-xs hover:underline">查看详情 →</span>
                      )}
                    </div>
                  </div>
                  {!notif.read && (
                    <button 
                      onClick={(e) => { e.stopPropagation(); onMarkRead(notif.id) }}
                      className="p-1 hover:bg-cyber-blue/20 rounded transition-colors"
                    >
                      <Check className="w-4 h-4 text-cyber-blue" />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </motion.div>
    </motion.div>
  )
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
    <Link href="/team">
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
    </Link>
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
  
  // 通知状态
  const [showNotifications, setShowNotifications] = useState(false)
  const [notifications, setNotifications] = useState<Array<{ id: string; title: string; content: string; time: string; read: boolean; action_url?: string }>>([])
  const [mounted, setMounted] = useState(false)
  
  // 客户端挂载后初始化通知（从真实API获取）
  useEffect(() => {
    setMounted(true)
    // 获取真实通知
    const fetchNotifications = async () => {
      try {
        const res = await fetch('/api/notifications?limit=10')
        if (res.ok) {
          const data = await res.json()
          if (data.items && data.items.length > 0) {
            setNotifications(data.items.map((n: any) => ({
              id: n.id,
              title: n.title,
              content: n.content,
              time: formatTime(n.created_at),
              read: n.is_read,
              action_url: n.action_url
            })))
          }
        }
      } catch (error) {
        console.error('获取通知失败:', error)
      }
    }
    fetchNotifications()
  }, [])
  
  const unreadCount = notifications.filter(n => !n.read).length
  
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
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])
  
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    return `${Math.floor(diff / 86400)}天前`
  }
  
  const handleMarkRead = async (id: string) => {
    try {
      // 调用后端API持久化已读状态
      const res = await fetch(`/api/notifications/${id}/read`, { method: 'PUT' })
      if (res.ok) {
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
      }
    } catch (error) {
      console.error('标记已读失败:', error)
      // 即使API失败，也更新本地状态以保持UI响应
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
    }
  }
  
  const handleClearAll = async () => {
    try {
      // 调用后端API标记所有为已读
      const res = await fetch('/api/notifications/read-all', { method: 'PUT' })
      if (res.ok) {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })))
      }
    } catch (error) {
      console.error('标记全部已读失败:', error)
      // 即使API失败，也更新本地状态
      setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    }
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
          <button 
            onClick={() => setShowNotifications(true)}
            className="p-2 glass-card hover:border-cyber-blue/50 transition-colors relative"
          >
            <Bell className="w-5 h-5 text-gray-400" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-alert-red text-white text-xs rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>
          <Link 
            href="/settings"
            className="p-2 glass-card hover:border-cyber-blue/50 transition-colors"
          >
            <Settings className="w-5 h-5 text-gray-400" />
          </Link>
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
            icon={Users}
            color="cyber-blue"
          />
          <StatCard 
            title="高意向客户" 
            value={stats.highIntent}
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
            change={stats.processing > 0 ? `${stats.processing} 处理中` : undefined}
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
      
      {/* 通知弹窗 */}
      <AnimatePresence>
        {showNotifications && (
          <NotificationsModal 
            isOpen={showNotifications}
            onClose={() => setShowNotifications(false)}
            notifications={notifications}
            onMarkRead={handleMarkRead}
            onClearAll={handleClearAll}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
