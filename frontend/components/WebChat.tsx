'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  MessageSquare, 
  X, 
  Send, 
  Loader2, 
  Minimize2, 
  Maximize2,
  User,
  Bot,
  Sparkles
} from 'lucide-react'

interface Message {
  content: string
  sender: 'user' | 'ai'
  timestamp: string
  type?: 'message' | 'system' | 'typing'
}

interface WebChatProps {
  position?: 'bottom-right' | 'bottom-left'
  primaryColor?: string
  title?: string
  subtitle?: string
}

export default function WebChat({
  position = 'bottom-right',
  primaryColor = '#00D4FF',
  title = '在线客服',
  subtitle = '欧洲物流专家为您服务'
}: WebChatProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
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
        console.log('WebSocket连接成功')
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
          } else if (data.type === 'pong') {
            // 心跳响应
          }
        } catch (e) {
          console.error('解析消息失败:', e)
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
        setConnectionError('连接失败，请刷新重试')
        setIsConnecting(false)
      }
      
      ws.onclose = () => {
        console.log('WebSocket关闭')
        wsRef.current = null
      }
      
      wsRef.current = ws
      
      // 心跳保活
      const heartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        } else {
          clearInterval(heartbeat)
        }
      }, 30000)
      
    } catch (error) {
      console.error('连接失败:', error)
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

  // 打开聊天窗口
  const handleOpen = useCallback(() => {
    setIsOpen(true)
    setIsMinimized(false)
    connectWebSocket()
  }, [connectWebSocket])

  // 关闭聊天窗口
  const handleClose = useCallback(() => {
    setIsOpen(false)
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  // 清理
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const positionClasses = position === 'bottom-right' 
    ? 'right-6 bottom-6' 
    : 'left-6 bottom-6'

  return (
    <div className={`fixed ${positionClasses} z-50`}>
      <AnimatePresence>
        {/* 聊天气泡按钮 */}
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleOpen}
            className="relative w-16 h-16 rounded-full shadow-2xl flex items-center justify-center group overflow-hidden"
            style={{ 
              background: `linear-gradient(135deg, ${primaryColor}, #A855F7)`,
              boxShadow: `0 8px 32px ${primaryColor}40`
            }}
          >
            <MessageSquare className="w-7 h-7 text-white" />
            
            {/* 脉冲动画 */}
            <span 
              className="absolute inset-0 rounded-full animate-ping opacity-30"
              style={{ backgroundColor: primaryColor }}
            />
            
            {/* 悬浮提示 */}
            <span className="absolute -top-12 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-3 py-1.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              💬 在线咨询
            </span>
          </motion.button>
        )}

        {/* 聊天窗口 */}
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 100, scale: 0.8 }}
            animate={{ 
              opacity: 1, 
              y: 0, 
              scale: 1,
              height: isMinimized ? 60 : 520
            }}
            exit={{ opacity: 0, y: 100, scale: 0.8 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="w-96 bg-gradient-to-b from-gray-900 to-gray-950 rounded-2xl shadow-2xl overflow-hidden border border-white/10"
            style={{ boxShadow: `0 25px 50px -12px ${primaryColor}30` }}
          >
            {/* 头部 */}
            <div 
              className="p-4 flex items-center justify-between cursor-pointer"
              onClick={() => setIsMinimized(!isMinimized)}
              style={{ 
                background: `linear-gradient(135deg, ${primaryColor}20, transparent)`
              }}
            >
              <div className="flex items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center"
                  style={{ backgroundColor: `${primaryColor}30` }}
                >
                  <Sparkles className="w-5 h-5" style={{ color: primaryColor }} />
                </div>
                <div>
                  <h3 className="font-semibold text-white">{title}</h3>
                  <p className="text-xs text-gray-400">{subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={(e) => { e.stopPropagation(); setIsMinimized(!isMinimized) }}
                  className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                >
                  {isMinimized ? (
                    <Maximize2 className="w-4 h-4 text-gray-400" />
                  ) : (
                    <Minimize2 className="w-4 h-4 text-gray-400" />
                  )}
                </button>
                <button 
                  onClick={(e) => { e.stopPropagation(); handleClose() }}
                  className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                >
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>
            </div>

            {/* 消息区域 */}
            {!isMinimized && (
              <>
                <div className="h-80 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
                  {isConnecting && (
                    <div className="flex items-center justify-center gap-2 text-gray-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm">连接中...</span>
                    </div>
                  )}
                  
                  {connectionError && (
                    <div className="text-center text-red-400 text-sm p-2 bg-red-500/10 rounded-lg">
                      {connectionError}
                    </div>
                  )}
                  
                  {messages.map((msg, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`flex items-start gap-2 max-w-[80%] ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                        {/* 头像 */}
                        <div 
                          className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                            msg.sender === 'user' 
                              ? 'bg-blue-500/30' 
                              : 'bg-gradient-to-br from-cyan-400/30 to-purple-500/30'
                          }`}
                        >
                          {msg.sender === 'user' ? (
                            <User className="w-4 h-4 text-blue-300" />
                          ) : (
                            <Bot className="w-4 h-4 text-cyan-300" />
                          )}
                        </div>
                        
                        {/* 消息内容 */}
                        <div 
                          className={`rounded-2xl px-4 py-2.5 ${
                            msg.sender === 'user'
                              ? 'bg-blue-500 text-white rounded-br-sm'
                              : 'bg-white/10 text-gray-100 rounded-bl-sm'
                          }`}
                        >
                          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                          <p className={`text-[10px] mt-1 ${
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
                  
                  {/* AI正在输入 */}
                  {isTyping && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-2"
                    >
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400/30 to-purple-500/30 flex items-center justify-center">
                        <Bot className="w-4 h-4 text-cyan-300" />
                      </div>
                      <div className="bg-white/10 rounded-2xl rounded-bl-sm px-4 py-3">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </motion.div>
                  )}
                  
                  <div ref={messagesEndRef} />
                </div>

                {/* 输入区域 */}
                <div className="p-4 border-t border-white/10">
                  <div className="flex gap-2">
                    <input
                      ref={inputRef}
                      type="text"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder="输入您的问题..."
                      disabled={isConnecting || !!connectionError}
                      className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400/50 transition-colors disabled:opacity-50"
                    />
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={sendMessage}
                      disabled={!inputValue.trim() || isConnecting || !!connectionError}
                      className="w-12 h-12 rounded-xl flex items-center justify-center transition-all disabled:opacity-50"
                      style={{ 
                        background: inputValue.trim() 
                          ? `linear-gradient(135deg, ${primaryColor}, #A855F7)` 
                          : 'rgba(255,255,255,0.1)'
                      }}
                    >
                      <Send className="w-5 h-5 text-white" />
                    </motion.button>
                  </div>
                  <p className="text-[10px] text-gray-500 mt-2 text-center">
                    由AI智能客服提供支持 · 24小时在线
                  </p>
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
