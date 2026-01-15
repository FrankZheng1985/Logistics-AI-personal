'use client'

import { useState, useEffect, useCallback } from 'react'
import { Bell, Check, AlertTriangle, User, Video, MessageSquare, Target, Trash2, CheckCircle, RefreshCw } from 'lucide-react'

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
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const [loading, setLoading] = useState(true)
  const [unreadCount, setUnreadCount] = useState(0)

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (filter === 'unread') {
        params.append('is_read', 'false')
      }
      
      const res = await fetch(`/api/notifications?${params}`)
      if (res.ok) {
        const data = await res.json()
        setNotifications(data.items || [])
        setUnreadCount(data.unread_count || 0)
      }
    } catch (error) {
      console.error('获取通知失败:', error)
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    fetchNotifications()
  }, [fetchNotifications])

  const filteredNotifications = notifications.filter(n => 
    filter === 'all' || !n.is_read
  )

  const markAsRead = async (id: string) => {
    try {
      const res = await fetch(`/api/notifications/${id}/read`, { method: 'PUT' })
      if (res.ok) {
        setNotifications(prev => prev.map(n => 
          n.id === id ? { ...n, is_read: true } : n
        ))
        setUnreadCount(prev => Math.max(0, prev - 1))
      }
    } catch (error) {
      console.error('标记已读失败:', error)
    }
  }

  const markAllAsRead = async () => {
    try {
      const res = await fetch('/api/notifications/read-all', { method: 'PUT' })
      if (res.ok) {
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
        setUnreadCount(0)
      }
    } catch (error) {
      console.error('标记全部已读失败:', error)
    }
  }

  const deleteNotification = async (id: string) => {
    try {
      const res = await fetch(`/api/notifications/${id}`, { method: 'DELETE' })
      if (res.ok) {
        const wasUnread = notifications.find(n => n.id === id)?.is_read === false
        setNotifications(prev => prev.filter(n => n.id !== id))
        if (wasUnread) {
          setUnreadCount(prev => Math.max(0, prev - 1))
        }
      }
    } catch (error) {
      console.error('删除通知失败:', error)
    }
  }

  const formatTime = (dateStr: string) => {
    if (!dateStr) return ''
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
          <button
            onClick={fetchNotifications}
            className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            title="刷新"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
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
        {loading ? (
          <div className="bg-dark-purple/40 rounded-xl p-12 text-center">
            <RefreshCw className="w-8 h-8 text-cyber-blue mx-auto mb-4 animate-spin" />
            <p className="text-gray-400">加载中...</p>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="bg-dark-purple/40 rounded-xl p-12 text-center">
            <Bell className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">暂无通知</p>
            <p className="text-gray-500 text-sm mt-2">
              系统会在有重要事件时通知您
            </p>
          </div>
        ) : (
          filteredNotifications.map(notification => {
            const IconComponent = typeIcons[notification.type] || Bell
            return (
              <div
                key={notification.id}
                className={`bg-dark-purple/40 rounded-xl p-5 border-l-4 ${priorityColors[notification.priority] || 'border-l-blue-500'} ${
                  !notification.is_read ? 'ring-1 ring-cyber-blue/30' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-lg ${typeColors[notification.type] || 'text-gray-400 bg-gray-400/10'}`}>
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
