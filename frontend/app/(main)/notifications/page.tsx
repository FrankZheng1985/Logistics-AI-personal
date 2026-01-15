'use client'

import { useState, useEffect } from 'react'
import { Bell, Check, AlertTriangle, User, Video, MessageSquare, Target, Trash2, CheckCircle } from 'lucide-react'

interface Notification {
  id: string
  type: 'high_intent' | 'task_complete' | 'system_alert' | 'lead_found' | 'video_ready'
  title: string
  content: string
  customer_id?: string
  customer_name?: string
  is_read: boolean
  priority: 'urgent' | 'high' | 'normal' | 'low'
  created_at: string
  action_url?: string
}

const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'high_intent',
    title: '🔥 发现高意向客户',
    content: '客户 "张经理" 意向分数达到 85 分，询问了美国海运报价和时效，建议立即跟进',
    customer_name: '张经理',
    is_read: false,
    priority: 'urgent',
    created_at: new Date().toISOString(),
    action_url: '/customers'
  },
  {
    id: '2',
    type: 'system_alert',
    title: '⚠️ API状态异常',
    content: '可灵AI视频接口响应时间超过5秒，可能影响视频生成速度',
    is_read: false,
    priority: 'high',
    created_at: new Date(Date.now() - 1800000).toISOString(),
    action_url: '/monitoring'
  },
  {
    id: '3',
    type: 'video_ready',
    title: '✅ 视频生成完成',
    content: '视频《FBA物流全流程解析》已生成完成，时长2分30秒',
    is_read: false,
    priority: 'normal',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    action_url: '/videos'
  },
  {
    id: '4',
    type: 'lead_found',
    title: '📍 发现新线索',
    content: '小猎在微博发现 3 条高质量物流需求线索，已自动分析和入库',
    is_read: true,
    priority: 'normal',
    created_at: new Date(Date.now() - 7200000).toISOString(),
    action_url: '/leads'
  },
  {
    id: '5',
    type: 'task_complete',
    title: '📝 日报已生成',
    content: '小调已完成今日AI团队工作日报，请查阅',
    is_read: true,
    priority: 'low',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    action_url: '/team/coordinator'
  }
]

const typeIcons: Record<string, any> = {
  high_intent: User,
  task_complete: CheckCircle,
  system_alert: AlertTriangle,
  lead_found: Target,
  video_ready: Video
}

const typeColors: Record<string, string> = {
  high_intent: 'text-green-400 bg-green-400/10',
  task_complete: 'text-blue-400 bg-blue-400/10',
  system_alert: 'text-yellow-400 bg-yellow-400/10',
  lead_found: 'text-purple-400 bg-purple-400/10',
  video_ready: 'text-cyan-400 bg-cyan-400/10'
}

const priorityColors: Record<string, string> = {
  urgent: 'border-l-red-500',
  high: 'border-l-orange-500',
  normal: 'border-l-blue-500',
  low: 'border-l-gray-500'
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications)
  const [filter, setFilter] = useState<'all' | 'unread'>('all')

  const filteredNotifications = notifications.filter(n => 
    filter === 'all' || !n.is_read
  )

  const unreadCount = notifications.filter(n => !n.is_read).length

  const markAsRead = (id: string) => {
    setNotifications(prev => prev.map(n => 
      n.id === id ? { ...n, is_read: true } : n
    ))
  }

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
  }

  const deleteNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
    return `${Math.floor(diff / 86400000)}天前`
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Bell className="w-7 h-7 text-cyber-blue" />
            通知中心
          </h1>
          <p className="text-gray-400 mt-1">
            {unreadCount > 0 ? `您有 ${unreadCount} 条未读通知` : '暂无未读通知'}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex bg-dark-purple/40 rounded-lg p-1">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                filter === 'all' 
                  ? 'bg-cyber-blue text-white' 
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              全部
            </button>
            <button
              onClick={() => setFilter('unread')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                filter === 'unread' 
                  ? 'bg-cyber-blue text-white' 
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              未读 {unreadCount > 0 && `(${unreadCount})`}
            </button>
          </div>
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="flex items-center gap-2 px-4 py-2 bg-dark-purple/40 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors"
            >
              <Check className="w-4 h-4" />
              全部已读
            </button>
          )}
        </div>
      </div>

      {/* 通知列表 */}
      <div className="space-y-3">
        {filteredNotifications.length === 0 ? (
          <div className="bg-dark-purple/40 rounded-xl p-12 text-center">
            <Bell className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">暂无通知</p>
          </div>
        ) : (
          filteredNotifications.map(notification => {
            const IconComponent = typeIcons[notification.type]
            return (
              <div
                key={notification.id}
                className={`bg-dark-purple/40 rounded-xl p-5 border-l-4 ${priorityColors[notification.priority]} ${
                  !notification.is_read ? 'ring-1 ring-cyber-blue/30' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-lg ${typeColors[notification.type]}`}>
                    <IconComponent className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className={`font-medium ${notification.is_read ? 'text-gray-300' : 'text-white'}`}>
                        {notification.title}
                      </h3>
                      {!notification.is_read && (
                        <span className="px-2 py-0.5 bg-cyber-blue/20 text-cyber-blue text-xs rounded-full">
                          新
                        </span>
                      )}
                    </div>
                    <p className="text-gray-400 text-sm mb-3">
                      {notification.content}
                    </p>
                    <div className="flex items-center gap-4">
                      <span className="text-gray-500 text-xs">
                        {formatTime(notification.created_at)}
                      </span>
                      {notification.action_url && (
                        <a
                          href={notification.action_url}
                          className="text-cyber-blue text-xs hover:underline"
                        >
                          查看详情 →
                        </a>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {!notification.is_read && (
                      <button
                        onClick={() => markAsRead(notification.id)}
                        className="p-2 text-gray-500 hover:text-green-400 hover:bg-green-400/10 rounded-lg transition-colors"
                        title="标记为已读"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => deleteNotification(notification.id)}
                      className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                      title="删除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
