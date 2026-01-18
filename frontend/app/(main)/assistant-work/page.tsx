'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Calendar, 
  CheckSquare, 
  Clock, 
  MapPin, 
  Plus,
  ChevronLeft,
  ChevronRight,
  Check,
  Trash2,
  Edit,
  FileText,
  AlertCircle,
  ArrowUp,
  ArrowDown,
  X
} from 'lucide-react'
import Link from 'next/link'

// 动画配置
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
}

// 优先级配置
const PRIORITY_CONFIG = {
  urgent: { label: '紧急', color: 'bg-red-500', textColor: 'text-red-400' },
  high: { label: '高', color: 'bg-orange-500', textColor: 'text-orange-400' },
  normal: { label: '普通', color: 'bg-blue-500', textColor: 'text-blue-400' },
  low: { label: '低', color: 'bg-gray-500', textColor: 'text-gray-400' }
}

// 格式化时间
function formatDateTime(isoString: string) {
  const date = new Date(isoString)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const month = date.getMonth() + 1
  const day = date.getDate()
  const weekday = weekdays[date.getDay()]
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return {
    date: `${month}月${day}日`,
    weekday,
    time: `${hours}:${minutes}`,
    full: `${month}月${day}日 ${weekday} ${hours}:${minutes}`
  }
}

// 统计卡片
function StatCard({ title, value, icon: Icon, color }: { 
  title: string
  value: number
  icon: any
  color: string
}) {
  return (
    <motion.div 
      variants={itemVariants}
      className="glass-card p-5"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm mb-1">{title}</p>
          <p className={`text-3xl font-bold font-number ${color}`}>{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${color.replace('text-', 'bg-')}/10`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
      </div>
    </motion.div>
  )
}

// 日程卡片
function ScheduleCard({ schedule, onComplete, onDelete }: {
  schedule: any
  onComplete: (id: string) => void
  onDelete: (id: string) => void
}) {
  const { date, weekday, time } = formatDateTime(schedule.start_time)
  const priority = PRIORITY_CONFIG[schedule.priority as keyof typeof PRIORITY_CONFIG] || PRIORITY_CONFIG.normal
  const isCompleted = schedule.status === 'completed'
  
  // 根据优先级设置边框颜色
  const borderColor = isCompleted ? '#4b5563' : 
    priority.color === 'bg-red-500' ? '#ef4444' :
    priority.color === 'bg-orange-500' ? '#f97316' :
    priority.color === 'bg-blue-500' ? '#3b82f6' : '#6b7280'
  
  return (
    <div 
      className={`glass-card p-4 border-l-4 ${isCompleted ? 'opacity-60' : ''}`}
      style={{ borderLeftColor: borderColor }}
    >
      <div className="flex items-start gap-3">
        <div className="text-center min-w-[60px]">
          <p className="text-cyber-blue font-bold text-lg">{date}</p>
          <p className="text-gray-400 text-sm">{weekday}</p>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className={`font-medium ${isCompleted ? 'line-through text-gray-500' : ''}`}>
              {schedule.title}
            </h3>
            <span className={`px-2 py-0.5 rounded text-xs ${priority.color} text-white`}>
              {priority.label}
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-400">
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              {time}
            </span>
            {schedule.location && (
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {schedule.location}
              </span>
            )}
          </div>
          {schedule.description && (
            <p className="text-gray-500 text-sm mt-2">{schedule.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!isCompleted && (
            <button 
              onClick={() => onComplete(schedule.id)}
              className="p-2 hover:bg-cyber-green/20 rounded-lg transition-colors"
              title="标记完成"
            >
              <Check className="w-4 h-4 text-cyber-green" />
            </button>
          )}
          <button 
            onClick={() => onDelete(schedule.id)}
            className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
            title="删除"
          >
            <Trash2 className="w-4 h-4 text-red-400" />
          </button>
        </div>
      </div>
    </div>
  )
}

// 待办卡片
function TodoCard({ todo, onComplete, onDelete }: {
  todo: any
  onComplete: (id: string) => void
  onDelete: (id: string) => void
}) {
  const priority = PRIORITY_CONFIG[todo.priority as keyof typeof PRIORITY_CONFIG] || PRIORITY_CONFIG.normal
  const isCompleted = todo.status === 'completed'
  
  return (
    <div className={`glass-card p-4 ${isCompleted ? 'opacity-60' : ''}`}>
      <div className="flex items-start gap-3">
        <button
          onClick={() => !isCompleted && onComplete(todo.id)}
          className={`mt-1 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
            isCompleted 
              ? 'bg-cyber-green border-cyber-green' 
              : 'border-gray-500 hover:border-cyber-blue'
          }`}
        >
          {isCompleted && <Check className="w-3 h-3 text-white" />}
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className={`font-medium ${isCompleted ? 'line-through text-gray-500' : ''}`}>
              {todo.title}
            </h3>
            <span className={`w-2 h-2 rounded-full ${priority.color}`} title={priority.label} />
          </div>
          {todo.description && (
            <p className="text-gray-500 text-sm mt-1">{todo.description}</p>
          )}
          {todo.due_date && (
            <p className="text-gray-400 text-xs mt-2">
              截止：{todo.due_date}
            </p>
          )}
        </div>
        <button 
          onClick={() => onDelete(todo.id)}
          className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
          title="删除"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// 添加日程弹窗
function AddScheduleModal({ isOpen, onClose, onAdd }: {
  isOpen: boolean
  onClose: () => void
  onAdd: (data: any) => void
}) {
  const [title, setTitle] = useState('')
  const [startTime, setStartTime] = useState('')
  const [location, setLocation] = useState('')
  const [priority, setPriority] = useState('normal')
  const [description, setDescription] = useState('')
  
  if (!isOpen) return null
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title || !startTime) return
    onAdd({
      title,
      start_time: new Date(startTime).toISOString(),
      location: location || null,
      priority,
      description: description || null
    })
    setTitle('')
    setStartTime('')
    setLocation('')
    setPriority('normal')
    setDescription('')
    onClose()
  }
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <motion.div 
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="glass-card w-full max-w-md mx-4 p-6"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">添加日程</h2>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">日程标题 *</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-cyber-blue outline-none"
              placeholder="例如：团队周会"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">开始时间 *</label>
            <input
              type="datetime-local"
              value={startTime}
              onChange={e => setStartTime(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-cyber-blue outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">地点</label>
            <input
              type="text"
              value={location}
              onChange={e => setLocation(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-cyber-blue outline-none"
              placeholder="例如：会议室A / 线上会议"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">优先级</label>
            <select
              value={priority}
              onChange={e => setPriority(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-cyber-blue outline-none"
            >
              <option value="low">低</option>
              <option value="normal">普通</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">备注</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-cyber-blue outline-none resize-none"
              rows={2}
              placeholder="可选备注信息"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-white/20 rounded-lg hover:bg-white/5 transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-cyber-blue rounded-lg hover:bg-cyber-blue/80 transition-colors font-medium"
            >
              添加
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}

// 添加待办弹窗
function AddTodoModal({ isOpen, onClose, onAdd }: {
  isOpen: boolean
  onClose: () => void
  onAdd: (data: any) => void
}) {
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState('normal')
  const [dueDate, setDueDate] = useState('')
  const [description, setDescription] = useState('')
  
  if (!isOpen) return null
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title) return
    onAdd({
      title,
      priority,
      due_date: dueDate || null,
      description: description || null
    })
    setTitle('')
    setPriority('normal')
    setDueDate('')
    setDescription('')
    onClose()
  }
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <motion.div 
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="glass-card w-full max-w-md mx-4 p-6"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">添加待办</h2>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">待办事项 *</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-cyber-blue outline-none"
              placeholder="例如：回复客户邮件"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">优先级</label>
            <select
              value={priority}
              onChange={e => setPriority(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-cyber-blue outline-none"
            >
              <option value="low">低</option>
              <option value="normal">普通</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">截止日期</label>
            <input
              type="date"
              value={dueDate}
              onChange={e => setDueDate(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-cyber-blue outline-none"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">描述</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-cyber-blue outline-none resize-none"
              rows={2}
              placeholder="可选描述信息"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-white/20 rounded-lg hover:bg-white/5 transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-cyber-blue rounded-lg hover:bg-cyber-blue/80 transition-colors font-medium"
            >
              添加
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}

export default function AssistantWorkPage() {
  const [stats, setStats] = useState({
    today_schedules: 0,
    tomorrow_schedules: 0,
    pending_todos: 0,
    completed_today: 0,
    total_meetings: 0
  })
  const [schedules, setSchedules] = useState<any[]>([])
  const [todos, setTodos] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddSchedule, setShowAddSchedule] = useState(false)
  const [showAddTodo, setShowAddTodo] = useState(false)
  const [activeTab, setActiveTab] = useState<'schedules' | 'todos'>('schedules')
  
  // 获取数据
  const fetchData = async () => {
    try {
      // 并行获取统计、日程、待办
      const [statsRes, schedulesRes, todosRes] = await Promise.all([
        fetch('/api/assistant/stats'),
        fetch('/api/assistant/schedules/upcoming?days=30'),
        fetch('/api/assistant/todos?status=pending')
      ])
      
      if (statsRes.ok) {
        const data = await statsRes.json()
        setStats(data)
      }
      
      if (schedulesRes.ok) {
        const data = await schedulesRes.json()
        setSchedules(data.items || [])
      }
      
      if (todosRes.ok) {
        const data = await todosRes.json()
        setTodos(data.items || [])
      }
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000) // 每分钟刷新
    return () => clearInterval(interval)
  }, [])
  
  // 添加日程
  const handleAddSchedule = async (data: any) => {
    try {
      const res = await fetch('/api/assistant/schedules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (res.ok) {
        fetchData()
      }
    } catch (error) {
      console.error('添加日程失败:', error)
    }
  }
  
  // 完成日程
  const handleCompleteSchedule = async (id: string) => {
    try {
      const res = await fetch(`/api/assistant/schedules/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'completed' })
      })
      if (res.ok) {
        fetchData()
      }
    } catch (error) {
      console.error('完成日程失败:', error)
    }
  }
  
  // 删除日程
  const handleDeleteSchedule = async (id: string) => {
    if (!confirm('确定要删除这个日程吗？')) return
    try {
      const res = await fetch(`/api/assistant/schedules/${id}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        fetchData()
      }
    } catch (error) {
      console.error('删除日程失败:', error)
    }
  }
  
  // 添加待办
  const handleAddTodo = async (data: any) => {
    try {
      const res = await fetch('/api/assistant/todos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (res.ok) {
        fetchData()
      }
    } catch (error) {
      console.error('添加待办失败:', error)
    }
  }
  
  // 完成待办
  const handleCompleteTodo = async (id: string) => {
    try {
      const res = await fetch(`/api/assistant/todos/${id}/complete`, {
        method: 'POST'
      })
      if (res.ok) {
        fetchData()
      }
    } catch (error) {
      console.error('完成待办失败:', error)
    }
  }
  
  // 删除待办
  const handleDeleteTodo = async (id: string) => {
    if (!confirm('确定要删除这个待办吗？')) return
    try {
      const res = await fetch(`/api/assistant/todos/${id}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        fetchData()
      }
    } catch (error) {
      console.error('删除待办失败:', error)
    }
  }
  
  return (
    <div className="min-h-screen p-6">
      {/* 顶部 */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Link href="/team" className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <ChevronLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center text-lg font-bold">
                助
              </div>
              小助工作台
            </h1>
            <p className="text-gray-400 mt-1">日程管理、待办事项、会议记录</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => setShowAddSchedule(true)}
            className="btn-cyber flex items-center gap-2"
          >
            <Calendar className="w-4 h-4" />
            添加日程
          </button>
          <button 
            onClick={() => setShowAddTodo(true)}
            className="btn-cyber flex items-center gap-2"
          >
            <CheckSquare className="w-4 h-4" />
            添加待办
          </button>
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
            title="今日日程" 
            value={stats.today_schedules}
            icon={Calendar}
            color="text-cyber-blue"
          />
          <StatCard 
            title="明日日程" 
            value={stats.tomorrow_schedules}
            icon={Clock}
            color="text-neon-purple"
          />
          <StatCard 
            title="待办事项" 
            value={stats.pending_todos}
            icon={CheckSquare}
            color="text-energy-orange"
          />
          <StatCard 
            title="今日完成" 
            value={stats.completed_today}
            icon={Check}
            color="text-cyber-green"
          />
        </div>
        
        {/* 标签切换 */}
        <div className="flex gap-4 border-b border-white/10">
          <button
            onClick={() => setActiveTab('schedules')}
            className={`pb-3 px-4 font-medium transition-colors relative ${
              activeTab === 'schedules' 
                ? 'text-cyber-blue' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <span className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              日程安排
              {schedules.length > 0 && (
                <span className="bg-cyber-blue/20 text-cyber-blue text-xs px-2 py-0.5 rounded-full">
                  {schedules.length}
                </span>
              )}
            </span>
            {activeTab === 'schedules' && (
              <motion.div 
                layoutId="activeTab"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyber-blue"
              />
            )}
          </button>
          <button
            onClick={() => setActiveTab('todos')}
            className={`pb-3 px-4 font-medium transition-colors relative ${
              activeTab === 'todos' 
                ? 'text-cyber-blue' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <span className="flex items-center gap-2">
              <CheckSquare className="w-4 h-4" />
              待办事项
              {todos.length > 0 && (
                <span className="bg-energy-orange/20 text-energy-orange text-xs px-2 py-0.5 rounded-full">
                  {todos.length}
                </span>
              )}
            </span>
            {activeTab === 'todos' && (
              <motion.div 
                layoutId="activeTab"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyber-blue"
              />
            )}
          </button>
        </div>
        
        {/* 内容区 */}
        <AnimatePresence mode="wait">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin w-8 h-8 border-2 border-cyber-blue border-t-transparent rounded-full" />
            </div>
          ) : activeTab === 'schedules' ? (
            <motion.div
              key="schedules"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-3"
            >
              {schedules.length === 0 ? (
                <div className="glass-card p-12 text-center">
                  <Calendar className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400">暂无日程安排</p>
                  <p className="text-gray-500 text-sm mt-1">通过企业微信告诉小助，或点击上方按钮添加</p>
                </div>
              ) : (
                schedules.map(schedule => (
                  <ScheduleCard 
                    key={schedule.id}
                    schedule={schedule}
                    onComplete={handleCompleteSchedule}
                    onDelete={handleDeleteSchedule}
                  />
                ))
              )}
            </motion.div>
          ) : (
            <motion.div
              key="todos"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-3"
            >
              {todos.length === 0 ? (
                <div className="glass-card p-12 text-center">
                  <CheckSquare className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400">暂无待办事项</p>
                  <p className="text-gray-500 text-sm mt-1">通过企业微信告诉小助，或点击上方按钮添加</p>
                </div>
              ) : (
                todos.map(todo => (
                  <TodoCard 
                    key={todo.id}
                    todo={todo}
                    onComplete={handleCompleteTodo}
                    onDelete={handleDeleteTodo}
                  />
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
      
      {/* 弹窗 */}
      <AddScheduleModal 
        isOpen={showAddSchedule}
        onClose={() => setShowAddSchedule(false)}
        onAdd={handleAddSchedule}
      />
      <AddTodoModal 
        isOpen={showAddTodo}
        onClose={() => setShowAddTodo(false)}
        onAdd={handleAddTodo}
      />
    </div>
  )
}
