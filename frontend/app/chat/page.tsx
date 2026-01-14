'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Send, 
  Loader2, 
  User,
  Bot,
  Sparkles,
  Globe,
  Truck,
  Package,
  Clock,
  CheckCircle2,
  ArrowLeft
} from 'lucide-react'
import Link from 'next/link'

interface Message {
  content: string
  sender: 'user' | 'ai'
  timestamp: string
  type?: 'message' | 'system' | 'typing'
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isConnecting, setIsConnecting] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  
  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 创建会话
  const createSession = useCallback(async () => {
    try {
      const response = await fetch('/api/webchat/session', { method: 'POST' })
      if (!response.ok) throw new Error('创建会话失败')
      const data = await response.json()
      return data.session_id
    } catch (error) {
      console.error('创建会话失败:', error)
      return null
    }
  }, [])

  // 连接WebSocket
  const connectWebSocket = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    
    setIsConnecting(true)
    setConnectionError(null)
    
    try {
      let sid = sessionId
      if (!sid) {
        sid = await createSession()
        if (!sid) throw new Error('无法创建会话')
        setSessionId(sid)
      }
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/api/webchat/ws/${sid}`
      
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        setIsConnecting(false)
        setConnectionError(null)
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'typing') {
            setIsTyping(true)
          } else if (data.type === 'message' || data.type === 'system') {
            setIsTyping(false)
            setMessages(prev => [...prev, {
              content: data.content,
              sender: data.sender,
              timestamp: data.timestamp || new Date().toISOString(),
              type: data.type
            }])
          }
        } catch (e) {
          console.error('解析消息失败:', e)
        }
      }
      
      ws.onerror = () => {
        setConnectionError('连接失败，请刷新重试')
        setIsConnecting(false)
      }
      
      ws.onclose = () => {
        wsRef.current = null
      }
      
      wsRef.current = ws
      
      const heartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        } else {
          clearInterval(heartbeat)
        }
      }, 30000)
      
    } catch (error) {
      setConnectionError('连接失败，请稍后重试')
      setIsConnecting(false)
    }
  }, [sessionId, createSession])

  // 发送消息
  const sendMessage = useCallback(() => {
    if (!inputValue.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    
    const message: Message = {
      content: inputValue.trim(),
      sender: 'user',
      timestamp: new Date().toISOString(),
      type: 'message'
    }
    
    setMessages(prev => [...prev, message])
    wsRef.current.send(JSON.stringify({ type: 'message', content: inputValue.trim() }))
    setInputValue('')
    inputRef.current?.focus()
  }, [inputValue])

  useEffect(() => {
    connectWebSocket()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connectWebSocket])

  // 快捷问题
  const quickQuestions = [
    { icon: <Truck className="w-4 h-4" />, text: '欧洲清关时效' },
    { icon: <Package className="w-4 h-4" />, text: '运费报价咨询' },
    { icon: <Globe className="w-4 h-4" />, text: '支持哪些国家' },
    { icon: <Clock className="w-4 h-4" />, text: '派送时间' },
  ]

  const handleQuickQuestion = (text: string) => {
    setInputValue(text)
    inputRef.current?.focus()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      {/* 背景装饰 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl" />
      </div>

      <div className="relative max-w-4xl mx-auto p-4 md:p-6">
        {/* 头部 */}
        <header className="mb-6">
          <div className="flex items-center gap-4 mb-4">
            <Link 
              href="/dashboard" 
              className="p-2 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-400" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">小销 · AI物流顾问</h1>
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  在线 · 24小时服务
                </div>
              </div>
            </div>
          </div>

          {/* 服务特点 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { icon: <Globe className="w-4 h-4" />, text: '覆盖全欧洲' },
              { icon: <CheckCircle2 className="w-4 h-4" />, text: '专业清关' },
              { icon: <Truck className="w-4 h-4" />, text: '门到门服务' },
              { icon: <Clock className="w-4 h-4" />, text: '实时追踪' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-gray-300">
                <span className="text-cyan-400">{item.icon}</span>
                {item.text}
              </div>
            ))}
          </div>
        </header>

        {/* 聊天区域 */}
        <div className="bg-gray-900/50 backdrop-blur-xl border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
          {/* 消息列表 */}
          <div className="h-[50vh] overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
            {isConnecting && (
              <div className="flex items-center justify-center gap-2 text-gray-400 py-8">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>正在连接...</span>
              </div>
            )}
            
            {connectionError && (
              <div className="text-center text-red-400 p-4 bg-red-500/10 rounded-xl">
                {connectionError}
              </div>
            )}
            
            {messages.length === 0 && !isConnecting && !connectionError && (
              <div className="text-center py-12">
                <div className="w-20 h-20 mx-auto mb-4 rounded-3xl bg-gradient-to-br from-cyan-400/20 to-purple-500/20 flex items-center justify-center">
                  <Bot className="w-10 h-10 text-cyan-400" />
                </div>
                <p className="text-gray-400 mb-6">您好！我是小销，专注欧洲物流服务。</p>
                <p className="text-gray-500 text-sm">有什么可以帮您的吗？</p>
              </div>
            )}
            
            {messages.map((msg, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex items-start gap-3 max-w-[75%] ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div 
                    className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      msg.sender === 'user' 
                        ? 'bg-blue-500/20' 
                        : 'bg-gradient-to-br from-cyan-400/20 to-purple-500/20'
                    }`}
                  >
                    {msg.sender === 'user' ? (
                      <User className="w-5 h-5 text-blue-400" />
                    ) : (
                      <Bot className="w-5 h-5 text-cyan-400" />
                    )}
                  </div>
                  
                  <div 
                    className={`rounded-2xl px-5 py-3 ${
                      msg.sender === 'user'
                        ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-br-sm'
                        : 'bg-white/10 text-gray-100 rounded-bl-sm'
                    }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    <p className={`text-xs mt-2 ${
                      msg.sender === 'user' ? 'text-blue-200' : 'text-gray-500'
                    }`}>
                      {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
            
            {isTyping && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-3"
              >
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400/20 to-purple-500/20 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-cyan-400" />
                </div>
                <div className="bg-white/10 rounded-2xl rounded-bl-sm px-5 py-4">
                  <div className="flex gap-1.5">
                    <span className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </motion.div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* 快捷问题 */}
          {messages.length === 0 && !isConnecting && (
            <div className="px-6 pb-4">
              <p className="text-xs text-gray-500 mb-3">快速咨询:</p>
              <div className="flex flex-wrap gap-2">
                {quickQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleQuickQuestion(q.text)}
                    className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full px-4 py-2 text-sm text-gray-300 transition-colors"
                  >
                    <span className="text-cyan-400">{q.icon}</span>
                    {q.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 输入区域 */}
          <div className="p-4 bg-black/20 border-t border-white/10">
            <div className="flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="输入您的问题..."
                disabled={isConnecting || !!connectionError}
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-5 py-4 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400/50 transition-colors disabled:opacity-50"
              />
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={sendMessage}
                disabled={!inputValue.trim() || isConnecting || !!connectionError}
                className="px-6 rounded-xl flex items-center gap-2 font-medium transition-all disabled:opacity-50"
                style={{ 
                  background: inputValue.trim() 
                    ? 'linear-gradient(135deg, #00D4FF, #A855F7)' 
                    : 'rgba(255,255,255,0.1)',
                  color: inputValue.trim() ? 'white' : '#9CA3AF'
                }}
              >
                <Send className="w-5 h-5" />
                发送
              </motion.button>
            </div>
            <p className="text-center text-xs text-gray-500 mt-3">
              🤖 AI智能客服 · 回复仅供参考 · 具体以实际报价为准
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
