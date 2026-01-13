'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { MessageSquare, User, Bot, ArrowLeft } from 'lucide-react'
import Link from 'next/link'

interface Conversation {
  id: string
  customer_name: string
  agent: string
  last_message: string
  timestamp: string
  messages_count: number
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const res = await fetch('/api/dashboard/recent-activities')
        if (res.ok) {
          const data = await res.json()
          // 将活动转换为对话格式
          if (data.activities && data.activities.length > 0) {
            setConversations(data.activities.map((a: any, i: number) => ({
              id: String(i),
              customer_name: '客户',
              agent: a.agent || '小销',
              last_message: a.content_preview || '暂无消息',
              timestamp: a.timestamp || new Date().toISOString(),
              messages_count: 1
            })))
          }
        }
      } catch (error) {
        console.error('Failed to fetch conversations:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchConversations()
  }, [])

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="min-h-screen p-6">
      {/* 顶部导航 */}
      <header className="flex items-center gap-4 mb-8">
        <Link href="/dashboard" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
          <ArrowLeft className="w-5 h-5 text-gray-400" />
        </Link>
        <div>
          <h1 className="text-2xl font-tech font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
            对话记录
          </h1>
          <p className="text-gray-400 mt-1">查看所有客户对话</p>
        </div>
      </header>

      {/* 对话列表 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="space-y-3"
      >
        {loading ? (
          <div className="glass-card p-8 text-center">
            <div className="animate-spin w-8 h-8 border-2 border-cyber-blue border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-400">加载中...</p>
          </div>
        ) : conversations.length === 0 ? (
          <div className="glass-card p-8 text-center">
            <MessageSquare className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-400 mb-2">暂无对话记录</p>
            <p className="text-gray-500 text-sm">当客户通过企业微信联系你时，对话会显示在这里</p>
          </div>
        ) : (
          conversations.map((conv, index) => (
            <motion.div
              key={conv.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="glass-card-hover p-4 cursor-pointer"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyber-blue/20 to-neon-purple/20 flex items-center justify-center">
                  <User className="w-6 h-6 text-cyber-blue" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium">{conv.customer_name}</span>
                    <span className="text-xs text-gray-500">与</span>
                    <span className="text-cyber-blue text-sm">[{conv.agent}]</span>
                  </div>
                  <p className="text-gray-400 text-sm truncate">{conv.last_message}</p>
                </div>
                <div className="text-right">
                  <p className="text-gray-500 text-xs">{formatTime(conv.timestamp)}</p>
                  <p className="text-cyber-blue text-sm">{conv.messages_count} 条消息</p>
                </div>
              </div>
            </motion.div>
          ))
        )}
      </motion.div>
    </div>
  )
}
