'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { MessageSquare, User, Bot, ArrowLeft, Send, Loader2, Search } from 'lucide-react'
import Link from 'next/link'

interface Message {
  id: string
  customer_id: string
  agent_type: string
  message_type: 'inbound' | 'outbound'
  content: string
  intent_delta: number
  created_at: string
}

interface CustomerConversation {
  customer_id: string
  customer_name: string
  messages: Message[]
  last_message: string
  last_time: string
}

// AI员工名称映射
const agentNames: Record<string, string> = {
  'coordinator': '小调',
  'sales': '小销',
  'analyst': '小析',
  'copywriter': '小文',
  'video_creator': '小视',
  'follow': '小跟',
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Message[]>([])
  const [customerConvs, setCustomerConvs] = useState<CustomerConversation[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    const fetchConversations = async () => {
      setLoading(true)
      try {
        // 获取所有对话
        const res = await fetch('/api/chat/conversations?page_size=100')
        if (res.ok) {
          const data = await res.json()
          if (data.items && data.items.length > 0) {
            setConversations(data.items)
            
            // 按客户分组对话
            const grouped = groupByCustomer(data.items)
            setCustomerConvs(grouped)
            
            // 默认选中第一个客户
            if (grouped.length > 0 && !selectedCustomer) {
              setSelectedCustomer(grouped[0].customer_id)
            }
          }
        }
      } catch (error) {
        console.error('获取对话列表失败:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchConversations()
    // 每15秒刷新
    const interval = setInterval(fetchConversations, 15000)
    return () => clearInterval(interval)
  }, [])

  // 按客户分组对话
  const groupByCustomer = (messages: Message[]): CustomerConversation[] => {
    const groups: Record<string, Message[]> = {}
    
    messages.forEach(msg => {
      if (!groups[msg.customer_id]) {
        groups[msg.customer_id] = []
      }
      groups[msg.customer_id].push(msg)
    })
    
    return Object.entries(groups).map(([customerId, msgs]) => {
      // 按时间排序
      const sorted = msgs.sort((a, b) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      )
      const lastMsg = sorted[sorted.length - 1]
      
      return {
        customer_id: customerId,
        customer_name: `客户 ${customerId.slice(0, 8)}`,
        messages: sorted,
        last_message: lastMsg.content.slice(0, 30) + (lastMsg.content.length > 30 ? '...' : ''),
        last_time: lastMsg.created_at
      }
    }).sort((a, b) => 
      new Date(b.last_time).getTime() - new Date(a.last_time).getTime()
    )
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  }

  const selectedConv = customerConvs.find(c => c.customer_id === selectedCustomer)
  
  // 过滤客户列表
  const filteredConvs = customerConvs.filter(c => 
    c.customer_name.includes(searchQuery) || 
    c.last_message.includes(searchQuery)
  )

  return (
    <div className="min-h-screen flex flex-col">
      {/* 顶部导航 */}
      <header className="flex items-center gap-4 p-6 border-b border-white/10">
        <Link href="/dashboard" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
          <ArrowLeft className="w-5 h-5 text-gray-400" />
        </Link>
        <div>
          <h1 className="text-2xl font-tech font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
            对话记录
          </h1>
          <p className="text-gray-400 mt-1">
            共 {customerConvs.length} 个客户，{conversations.length} 条消息
          </p>
        </div>
      </header>

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧客户列表 */}
        <div className="w-80 border-r border-white/10 flex flex-col">
          {/* 搜索框 */}
          <div className="p-4 border-b border-white/10">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="搜索对话..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-dark-purple/50 border border-white/10 rounded-lg focus:border-cyber-blue/50 focus:outline-none text-sm"
              />
            </div>
          </div>
          
          {/* 客户列表 */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center">
                <Loader2 className="w-6 h-6 animate-spin text-cyber-blue mx-auto mb-2" />
                <p className="text-gray-500 text-sm">加载中...</p>
              </div>
            ) : filteredConvs.length === 0 ? (
              <div className="p-8 text-center">
                <MessageSquare className="w-10 h-10 text-gray-600 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">暂无对话</p>
              </div>
            ) : (
              filteredConvs.map((conv) => (
                <motion.div
                  key={conv.customer_id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  onClick={() => setSelectedCustomer(conv.customer_id)}
                  className={`p-4 border-b border-white/5 cursor-pointer transition-colors ${
                    selectedCustomer === conv.customer_id 
                      ? 'bg-cyber-blue/10 border-l-2 border-l-cyber-blue' 
                      : 'hover:bg-white/5'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyber-blue/20 to-neon-purple/20 flex items-center justify-center">
                      <User className="w-5 h-5 text-cyber-blue" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">{conv.customer_name}</span>
                        <span className="text-xs text-gray-500">{formatTime(conv.last_time)}</span>
                      </div>
                      <p className="text-gray-400 text-xs truncate">{conv.last_message}</p>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs text-gray-500">{conv.messages.length} 条消息</span>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </div>

        {/* 右侧对话详情 */}
        <div className="flex-1 flex flex-col bg-dark-purple/20">
          {selectedConv ? (
            <>
              {/* 客户信息头部 */}
              <div className="p-4 border-b border-white/10 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center">
                  <User className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="font-medium">{selectedConv.customer_name}</p>
                  <p className="text-xs text-gray-500">{selectedConv.messages.length} 条对话记录</p>
                </div>
              </div>
              
              {/* 对话消息列表 */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {selectedConv.messages.map((msg, index) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.02 }}
                    className={`flex ${msg.message_type === 'inbound' ? 'justify-start' : 'justify-end'}`}
                  >
                    <div className={`max-w-[70%] ${msg.message_type === 'inbound' ? '' : 'order-1'}`}>
                      {/* 发送者标识 */}
                      <div className={`flex items-center gap-2 mb-1 ${msg.message_type === 'inbound' ? '' : 'justify-end'}`}>
                        {msg.message_type === 'inbound' ? (
                          <>
                            <User className="w-3 h-3 text-gray-500" />
                            <span className="text-xs text-gray-500">客户</span>
                          </>
                        ) : (
                          <>
                            <span className="text-xs text-cyber-blue">[{agentNames[msg.agent_type] || msg.agent_type}]</span>
                            <Bot className="w-3 h-3 text-cyber-blue" />
                          </>
                        )}
                        <span className="text-xs text-gray-600">{formatTime(msg.created_at)}</span>
                      </div>
                      
                      {/* 消息内容 */}
                      <div className={`p-3 rounded-lg ${
                        msg.message_type === 'inbound' 
                          ? 'bg-white/10 text-gray-200' 
                          : 'bg-cyber-blue/20 border border-cyber-blue/30 text-gray-200'
                      }`}>
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      </div>
                      
                      {/* 意向值变化 */}
                      {msg.intent_delta > 0 && (
                        <p className="text-xs text-cyber-green mt-1 text-right">+{msg.intent_delta} 意向分</p>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
              
              {/* 底部提示 */}
              <div className="p-4 border-t border-white/10 text-center">
                <p className="text-gray-500 text-xs">
                  💡 消息由企业微信实时同步，AI员工自动回复
                </p>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageSquare className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">选择一个对话查看详情</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
