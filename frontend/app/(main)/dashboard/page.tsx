'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Users, 
  MessageSquare, 
  TrendingUp,
  Bot,
  Bell,
  Settings,
  X,
  Check,
  Activity,
  Zap,
  Radio
} from 'lucide-react'
import Link from 'next/link'

// 动画配置
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
}

// 数字跳动动画组件
function AnimatedNumber({ value, duration = 1000 }: { value: number; duration?: number }) {
  const [displayValue, setDisplayValue] = useState(0)
  
  useEffect(() => {
    if (value === 0) {
      setDisplayValue(0)
      return
    }
    
    let startTime: number
    let animationFrame: number
    
    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp
      const progress = Math.min((timestamp - startTime) / duration, 1)
      
      // easeOutExpo for smooth deceleration
      const eased = 1 - Math.pow(2, -10 * progress)
      setDisplayValue(Math.floor(eased * value))
      
      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate)
      }
    }
    
    animationFrame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animationFrame)
  }, [value, duration])
  
  return <span>{displayValue}</span>
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

// HUD 统计指标卡片
function HUDStatCard({ 
  title, 
  value, 
  icon: Icon,
  color = 'cyber-blue',
  glowColor = 'rgba(0, 212, 255, 0.3)'
}: {
  title: string
  value: number
  icon: any
  color?: string
  glowColor?: string
}) {
  return (
    <motion.div 
      variants={itemVariants}
      className="relative overflow-hidden"
    >
      {/* 背景光效 */}
      <div 
        className="absolute inset-0 opacity-20"
        style={{ 
          background: `radial-gradient(ellipse at center, ${glowColor} 0%, transparent 70%)`
        }}
      />
      
      {/* 边框光效 */}
      <div className={`glass-card p-4 md:p-5 border-t-2 border-${color}`} style={{ borderTopColor: glowColor }}>
        <div className="flex items-center justify-between relative z-10">
          <div>
            <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">{title}</p>
            <p className={`text-3xl md:text-4xl font-bold font-number text-${color}`}>
              <AnimatedNumber value={value} />
            </p>
          </div>
          <div className={`p-3 rounded-lg bg-${color}/10`}>
            <Icon className={`w-6 h-6 text-${color}`} style={{ color: glowColor }} />
          </div>
        </div>
        
        {/* 底部扫描线动画 */}
        <div className="absolute bottom-0 left-0 right-0 h-0.5 overflow-hidden">
          <motion.div 
            className="h-full w-1/3"
            style={{ background: `linear-gradient(90deg, transparent, ${glowColor}, transparent)` }}
            animate={{ x: ['-100%', '400%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          />
        </div>
      </div>
    </motion.div>
  )
}

// 打字效果 Hook
function useTypingEffect(text: string | null, speed = 30) {
  const [displayText, setDisplayText] = useState('')
  
  useEffect(() => {
    if (!text) {
      setDisplayText('')
      return
    }
    
    setDisplayText('')
    let index = 0
    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayText(text.slice(0, index + 1))
        index++
      } else {
        clearInterval(timer)
      }
    }, speed)
    
    return () => clearInterval(timer)
  }, [text, speed])
  
  return displayText
}

// AI 员工指挥卡片（新版）
function AgentCommandCard({ 
  name, 
  role, 
  status, 
  currentTask,
  tasksToday,
  lastActive
}: {
  name: string
  role: string
  status: 'online' | 'busy' | 'offline'
  currentTask: string | null
  tasksToday: number
  lastActive: string | null
}) {
  const typedTask = useTypingEffect(currentTask, 25)
  
  const statusConfig = {
    online: { 
      label: '待命', 
      bgColor: 'bg-cyber-green', 
      glowColor: 'shadow-[0_0_12px_rgba(0,255,136,0.5)]',
      ringColor: 'ring-cyber-green/50'
    },
    busy: { 
      label: '执行中', 
      bgColor: 'bg-energy-orange', 
      glowColor: 'shadow-[0_0_12px_rgba(255,107,53,0.5)]',
      ringColor: 'ring-energy-orange/50'
    },
    offline: { 
      label: '离线', 
      bgColor: 'bg-gray-500', 
      glowColor: '',
      ringColor: 'ring-gray-500/30'
    }
  }
  
  const config = statusConfig[status]
  
  return (
    <motion.div 
      variants={itemVariants}
      className="glass-card p-4 relative overflow-hidden group hover:border-cyber-blue/30 transition-all duration-300"
    >
      {/* 左侧状态条 */}
      <div 
        className={`absolute left-0 top-0 bottom-0 w-1 ${config.bgColor}`}
        style={{ opacity: status === 'busy' ? 1 : 0.6 }}
      />
      
      {/* 头部信息 */}
      <div className="flex items-center gap-3 mb-3">
        {/* 头像 + 状态指示灯 */}
        <div className="relative">
          <div className={`w-11 h-11 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center text-lg font-bold ring-2 ${config.ringColor}`}>
            {name[0]}
          </div>
          {/* 呼吸灯状态点 */}
          <div 
            className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full ${config.bgColor} ${config.glowColor} ${status === 'busy' ? 'animate-pulse' : ''}`}
          />
        </div>
        
        {/* 名称和角色 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white">{name}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${config.bgColor}/20 text-${status === 'busy' ? 'energy-orange' : status === 'online' ? 'cyber-green' : 'gray-400'}`}>
              {config.label}
            </span>
          </div>
          <p className="text-gray-500 text-xs">{role}</p>
        </div>
        
        {/* 今日任务数 */}
        <div className="text-right">
          <p className="text-xl font-number font-bold text-cyber-blue">{tasksToday}</p>
          <p className="text-gray-600 text-[10px]">今日任务</p>
        </div>
      </div>
      
      {/* 当前任务显示区域（终端风格） */}
      <div className="bg-black/40 rounded-lg p-2.5 min-h-[48px] border border-white/5">
        {currentTask ? (
          <div className="flex items-start gap-2">
            <Zap className="w-3.5 h-3.5 text-energy-orange flex-shrink-0 mt-0.5 animate-pulse" />
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-energy-orange mb-0.5">正在执行:</p>
              <p className="text-xs text-gray-300 font-mono leading-relaxed">
                {typedTask}
                <span className="animate-pulse text-cyber-blue">|</span>
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-gray-600">
            <Radio className="w-3.5 h-3.5" />
            <span className="text-xs font-mono">等待任务分配...</span>
          </div>
        )}
      </div>
      
      {/* 波形动画（仅在执行中显示） - 使用固定值避免 hydration 错误 */}
      {status === 'busy' && (
        <div className="absolute bottom-0 left-1 right-0 h-0.5 flex items-end justify-around opacity-60">
          {[3, 5, 4, 7, 3, 6, 4, 5, 8, 4, 6, 3, 5, 7, 4, 6, 3, 5, 4, 6].map((h, i) => (
            <motion.div
              key={i}
              className="w-0.5 bg-energy-orange rounded-full"
              animate={{ 
                height: [2, h, 2],
              }}
              transition={{
                duration: 0.5 + (i % 5) * 0.1,
                repeat: Infinity,
                delay: i * 0.05
              }}
            />
          ))}
        </div>
      )}
    </motion.div>
  )
}

// 系统终端日志组件
function SystemTerminal({ 
  activities 
}: { 
  activities: Array<{ agent: string; action: string; time: string }> 
}) {
  const terminalRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [activities])
  
  return (
    <motion.div variants={itemVariants} className="h-full flex flex-col">
      {/* 终端标题栏 */}
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-cyber-green" />
        <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider">System Log</h2>
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-alert-red" />
          <div className="w-2 h-2 rounded-full bg-energy-orange" />
          <div className="w-2 h-2 rounded-full bg-cyber-green" />
        </div>
      </div>
      
      {/* 终端内容区 */}
      <div 
        ref={terminalRef}
        className="flex-1 bg-black/60 rounded-lg p-3 font-mono text-xs overflow-y-auto border border-white/5 space-y-1.5"
        style={{ maxHeight: '340px' }}
      >
        {activities.length === 0 ? (
          <div className="text-gray-600">
            <span className="text-cyber-green">$</span> 等待系统日志...
          </div>
        ) : (
          activities.map((activity, index) => (
            <motion.div 
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="flex items-start gap-2 group hover:bg-white/5 px-1 py-0.5 rounded"
            >
              <span className="text-gray-600 flex-shrink-0">{activity.time}</span>
              <span className="text-cyber-blue flex-shrink-0">[{activity.agent}]</span>
              <span className="text-gray-400 break-all">{activity.action}</span>
            </motion.div>
          ))
        )}
        
        {/* 光标闪烁 */}
        <div className="flex items-center gap-1 text-cyber-green pt-1">
          <span>$</span>
          <span className="animate-pulse">_</span>
        </div>
      </div>
    </motion.div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState({
    newCustomers: 0,
    highIntent: 0,
    conversations: 0
  })
  
  const [agents, setAgents] = useState<Array<{
    name: string
    type: string
    role: string
    status: 'online' | 'busy' | 'offline'
    currentTask: string | null
    tasksToday: number
    lastActive: string | null
  }>>([])
  
  const [activities, setActivities] = useState<Array<{agent: string; action: string; time: string}>>([])
  const [loading, setLoading] = useState(true)
  
  // 通知状态
  const [showNotifications, setShowNotifications] = useState(false)
  const [notifications, setNotifications] = useState<Array<{ id: string; title: string; content: string; time: string; read: boolean; action_url?: string }>>([])
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
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
            conversations: statsData.today?.conversations || 0
          })
        }
        
        // 获取AI团队状态（包含当前任务）
        const teamRes = await fetch('/api/dashboard/team-status')
        if (teamRes.ok) {
          const teamData = await teamRes.json()
          if (teamData.agents && teamData.agents.length > 0) {
            setAgents(teamData.agents.map((a: any) => ({
              name: a.name,
              type: a.type,
              role: a.role || '未知',
              status: a.status || 'online',
              currentTask: a.current_task || null,
              tasksToday: a.tasks_today || 0,
              lastActive: a.last_active || null
            })))
          }
        }
        
        // 获取最近活动
        const activitiesRes = await fetch('/api/dashboard/recent-activities')
        if (activitiesRes.ok) {
          const activitiesData = await activitiesRes.json()
          if (activitiesData.activities && activitiesData.activities.length > 0) {
            setActivities(activitiesData.activities.map((a: any) => ({
              agent: a.agent || '系统',
              action: a.content_preview || a.action || '活动记录',
              time: formatTimeShort(a.timestamp)
            })))
          } else {
            setActivities([{ agent: '系统', action: '系统启动完成，等待任务...', time: formatTimeShort(new Date().toISOString()) }])
          }
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
    const interval = setInterval(fetchData, 15000) // 15秒刷新
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
  
  const formatTimeShort = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
  
  const handleMarkRead = async (id: string) => {
    try {
      const res = await fetch(`/api/notifications/${id}/read`, { method: 'PUT' })
      if (res.ok) {
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
      }
    } catch (error) {
      console.error('标记已读失败:', error)
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
    }
  }
  
  const handleClearAll = async () => {
    try {
      const res = await fetch('/api/notifications/read-all', { method: 'PUT' })
      if (res.ok) {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })))
      }
    } catch (error) {
      console.error('标记全部已读失败:', error)
      setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    }
  }
  
  // 获取当前时间（客户端挂载后才显示，避免 hydration 错误）
  const [currentTime, setCurrentTime] = useState<Date | null>(null)
  useEffect(() => {
    setCurrentTime(new Date()) // 初始化
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])
  
  return (
    <div className="min-h-screen relative">
      {/* 背景网格增强 */}
      <div className="fixed inset-0 pointer-events-none opacity-30">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>
      
      {/* 顶部指挥中心头部 */}
      <header className="relative mb-6 md:mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* 左侧标题区 */}
          <div>
            <div className="flex items-center gap-3">
              <div className="w-2 h-8 bg-gradient-to-b from-cyber-blue to-neon-purple rounded-full" />
              <div>
                <h1 className="text-2xl md:text-3xl font-bold font-tech tracking-wide">
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue via-white to-neon-purple">
                    AI 指挥中心
                  </span>
                </h1>
                <p className="text-gray-500 text-sm">Command Center · 物流智能获客系统</p>
              </div>
            </div>
          </div>
          
          {/* 右侧状态区 */}
          <div className="flex items-center gap-3 sm:gap-4">
            {/* 系统时间 */}
            <div className="hidden md:block text-right" suppressHydrationWarning>
              <p className="text-cyber-blue font-mono text-lg font-bold">
                {currentTime ? currentTime.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--:--'}
              </p>
              <p className="text-gray-600 text-xs">
                {currentTime ? currentTime.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', weekday: 'short' }) : '--'}
              </p>
            </div>
            
            <div className="h-8 w-px bg-white/10 hidden md:block" />
            
            <button 
              onClick={() => setShowNotifications(true)}
              className="p-2 glass-card hover:border-cyber-blue/50 transition-colors relative"
            >
              <Bell className="w-5 h-5 text-gray-400" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-alert-red text-white text-xs rounded-full flex items-center justify-center animate-pulse">
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
          </div>
        </div>
        
        {/* 状态指示条 */}
        <div className="mt-4 flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-cyber-green animate-pulse" />
            <span className="text-gray-500">系统在线</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-cyber-blue" />
            <span className="text-gray-500">{agents.filter(a => a.status !== 'offline').length} 个AI在线</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-energy-orange" />
            <span className="text-gray-500">{agents.filter(a => a.status === 'busy').length} 个执行中</span>
          </div>
        </div>
      </header>
      
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="space-y-6"
      >
        {/* HUD 统计指标 */}
        <div className="grid grid-cols-3 gap-4">
          <HUDStatCard 
            title="今日获客" 
            value={stats.newCustomers}
            icon={Users}
            color="cyber-blue"
            glowColor="rgba(0, 212, 255, 0.4)"
          />
          <HUDStatCard 
            title="高意向" 
            value={stats.highIntent}
            icon={TrendingUp}
            color="cyber-green"
            glowColor="rgba(0, 255, 136, 0.4)"
          />
          <HUDStatCard 
            title="对话数" 
            value={stats.conversations}
            icon={MessageSquare}
            color="neon-purple"
            glowColor="rgba(139, 92, 246, 0.4)"
          />
        </div>
        
        {/* 主内容区：AI员工监控 + 系统日志 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* AI 员工监控矩阵 */}
          <motion.div variants={itemVariants} className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-cyber-blue" />
                <h2 className="text-lg font-bold text-white">AI 员工状态</h2>
              </div>
              <Link 
                href="/team" 
                className="text-cyber-blue hover:text-cyber-blue/80 text-xs flex items-center gap-1"
              >
                详细管理 →
              </Link>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {agents.length > 0 ? (
                agents.map((agent) => (
                  <AgentCommandCard 
                    key={agent.type} 
                    name={agent.name}
                    role={agent.role}
                    status={agent.status}
                    currentTask={agent.currentTask}
                    tasksToday={agent.tasksToday}
                    lastActive={agent.lastActive}
                  />
                ))
              ) : (
                // Loading skeleton
                [...Array(6)].map((_, i) => (
                  <div key={i} className="glass-card p-4 animate-pulse">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-11 h-11 rounded-full bg-white/10" />
                      <div className="flex-1">
                        <div className="h-4 bg-white/10 rounded w-20 mb-1" />
                        <div className="h-3 bg-white/5 rounded w-16" />
                      </div>
                    </div>
                    <div className="h-12 bg-black/40 rounded-lg" />
                  </div>
                ))
              )}
            </div>
          </motion.div>
          
          {/* 系统终端日志 */}
          <SystemTerminal activities={activities} />
        </div>
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
