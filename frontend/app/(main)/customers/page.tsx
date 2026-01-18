'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Search, 
  Filter, 
  ChevronDown,
  Phone,
  MessageSquare,
  TrendingUp,
  MoreVertical,
  ArrowLeft,
  Loader2,
  Users,
  X,
  Mail,
  Building,
  Calendar,
  Activity,
  Send,
  Globe
} from 'lucide-react'
import Link from 'next/link'

interface Customer {
  id: string
  name: string
  company: string | null
  intentLevel: 'S' | 'A' | 'B' | 'C'
  intentScore: number
  phone: string | null
  email: string | null
  source: string
  lastContact: string | null
  createdAt: string | null
  language: 'auto' | 'zh' | 'en'
}

// 意向等级徽章
function IntentBadge({ level }: { level: 'S' | 'A' | 'B' | 'C' }) {
  const config = {
    S: { class: 'intent-s', label: 'S级' },
    A: { class: 'intent-a', label: 'A级' },
    B: { class: 'intent-b', label: 'B级' },
    C: { class: 'intent-c', label: 'C级' },
  }
  return <span className={config[level].class}>{config[level].label}</span>
}

// 语言选择器
function LanguageSelector({ 
  customerId, 
  currentLanguage, 
  onUpdate 
}: { 
  customerId: string
  currentLanguage: 'auto' | 'zh' | 'en'
  onUpdate?: () => void
}) {
  const [language, setLanguage] = useState(currentLanguage)
  const [saving, setSaving] = useState(false)
  
  const languageOptions = [
    { value: 'auto', label: '自动检测', flag: '🔄' },
    { value: 'zh', label: '中文', flag: '🇨🇳' },
    { value: 'en', label: 'English', flag: '🇬🇧' },
  ]
  
  const handleChange = async (newLang: string) => {
    setLanguage(newLang as any)
    setSaving(true)
    
    try {
      const res = await fetch(`/api/customers/${customerId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: newLang })
      })
      
      if (res.ok) {
        onUpdate?.()
      } else {
        console.error('更新语言失败')
        setLanguage(currentLanguage) // 回滚
      }
    } catch (error) {
      console.error('更新语言失败:', error)
      setLanguage(currentLanguage) // 回滚
    } finally {
      setSaving(false)
    }
  }
  
  const currentOption = languageOptions.find(opt => opt.value === language)
  
  return (
    <div className="relative">
      <select
        value={language}
        onChange={e => handleChange(e.target.value)}
        disabled={saving}
        className="w-full px-3 py-1.5 text-sm bg-dark-purple/50 border border-white/10 rounded-lg 
                   focus:border-cyber-blue/50 focus:outline-none appearance-none cursor-pointer
                   disabled:opacity-50"
      >
        {languageOptions.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.flag} {opt.label}
          </option>
        ))}
      </select>
      {saving && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2">
          <Loader2 className="w-3 h-3 animate-spin text-cyber-blue" />
        </div>
      )}
    </div>
  )
}

// 客户详情弹窗
function CustomerDetailModal({ 
  customer, 
  onClose,
  onSendMessage,
  onRefresh
}: { 
  customer: Customer | null
  onClose: () => void
  onSendMessage: (customerId: string, message: string) => void
  onRefresh?: () => void
}) {
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [emailContent, setEmailContent] = useState('')
  const [sendingEmail, setSendingEmail] = useState(false)
  const [showEmailForm, setShowEmailForm] = useState(false)
  const [editingEmail, setEditingEmail] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [savingEmail, setSavingEmail] = useState(false)
  
  if (!customer) return null
  
  const handleSend = async () => {
    if (!message.trim()) return
    setSending(true)
    await onSendMessage(customer.id, message)
    setMessage('')
    setSending(false)
  }
  
  // 发送跟进邮件
  const handleSendEmail = async () => {
    if (!customer.email) {
      alert('该客户没有邮箱地址，请先添加')
      return
    }
    
    setSendingEmail(true)
    try {
      const res = await fetch('/api/follow/ai-follow-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_id: customer.id,
          purpose: 'daily_follow',
          custom_content: emailContent.trim() || undefined
        })
      })
      
      const data = await res.json()
      
      if (data.success) {
        alert(`✅ ${data.message}`)
        setEmailContent('')
        setShowEmailForm(false)
        onRefresh?.()
      } else {
        alert(`❌ ${data.message || data.error || '发送失败'}`)
      }
    } catch (error) {
      console.error('发送邮件失败:', error)
      alert('发送失败，请稍后重试')
    } finally {
      setSendingEmail(false)
    }
  }
  
  // 保存客户邮箱
  const handleSaveEmail = async () => {
    if (!newEmail.trim()) {
      setEditingEmail(false)
      return
    }
    
    // 验证邮箱格式
    const emailRegex = /^[\w\.-]+@[\w\.-]+\.\w+$/
    if (!emailRegex.test(newEmail.trim())) {
      alert('请输入正确的邮箱格式')
      return
    }
    
    setSavingEmail(true)
    try {
      const res = await fetch(`/api/customers/${customer.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: newEmail.trim() })
      })
      
      if (res.ok) {
        alert('邮箱保存成功！')
        customer.email = newEmail.trim()
        setEditingEmail(false)
        onRefresh?.()
      } else {
        alert('保存失败，请重试')
      }
    } catch (error) {
      console.error('保存邮箱失败:', error)
      alert('保存失败，请稍后重试')
    } finally {
      setSavingEmail(false)
    }
  }
  
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      onClick={onClose}
    >
      <motion.div 
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className="glass-card w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-dark-purple to-cyber-blue/30 flex items-center justify-center text-2xl font-bold">
              {customer.name?.[0] || '?'}
            </div>
            <div>
              <h2 className="text-xl font-bold">{customer.name}</h2>
              <div className="flex items-center gap-2 mt-1">
                <IntentBadge level={customer.intentLevel} />
                <span className="text-gray-400 text-sm">意向分: <span className="text-cyber-blue font-number">{customer.intentScore}</span></span>
              </div>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* 信息 */}
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card p-4">
              <div className="flex items-center gap-2 text-gray-400 mb-1">
                <Building className="w-4 h-4" />
                公司
              </div>
              <p className="font-medium">{customer.company || '未知'}</p>
            </div>
            <div className="glass-card p-4">
              <div className="flex items-center gap-2 text-gray-400 mb-1">
                <Phone className="w-4 h-4" />
                电话
              </div>
              <p className="font-medium">{customer.phone || '未知'}</p>
            </div>
            {/* 邮箱 */}
            <div className="glass-card p-4">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2 text-gray-400">
                  <Mail className="w-4 h-4" />
                  邮箱
                </div>
                {!editingEmail && (
                  <button 
                    onClick={() => {
                      setNewEmail(customer.email || '')
                      setEditingEmail(true)
                    }}
                    className="text-xs text-cyber-blue hover:underline"
                  >
                    {customer.email ? '修改' : '添加'}
                  </button>
                )}
              </div>
              {editingEmail ? (
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={newEmail}
                    onChange={e => setNewEmail(e.target.value)}
                    placeholder="输入邮箱地址..."
                    className="flex-1 px-2 py-1 text-sm bg-dark-purple/50 border border-white/10 rounded focus:border-cyber-blue/50 focus:outline-none"
                    autoFocus
                  />
                  <button 
                    onClick={handleSaveEmail}
                    disabled={savingEmail}
                    className="px-2 py-1 text-xs bg-cyber-blue text-black rounded hover:bg-cyber-blue/80 disabled:opacity-50"
                  >
                    {savingEmail ? '...' : '保存'}
                  </button>
                  <button 
                    onClick={() => setEditingEmail(false)}
                    className="px-2 py-1 text-xs text-gray-400 hover:text-white"
                  >
                    取消
                  </button>
                </div>
              ) : (
                <p className="font-medium">{customer.email || <span className="text-gray-500">未设置</span>}</p>
              )}
            </div>
            <div className="glass-card p-4">
              <div className="flex items-center gap-2 text-gray-400 mb-1">
                <Activity className="w-4 h-4" />
                来源
              </div>
              <p className="font-medium">{customer.source}</p>
            </div>
            {/* 语言偏好 */}
            <div className="glass-card p-4">
              <div className="flex items-center gap-2 text-gray-400 mb-1">
                <Globe className="w-4 h-4" />
                语言偏好
              </div>
              <LanguageSelector 
                customerId={customer.id} 
                currentLanguage={customer.language || 'auto'} 
                onUpdate={onRefresh}
              />
            </div>
            <div className="glass-card p-4">
              <div className="flex items-center gap-2 text-gray-400 mb-1">
                <Calendar className="w-4 h-4" />
                最近联系
              </div>
              <p className="font-medium">{customer.lastContact || '从未联系'}</p>
            </div>
          </div>
          
          {/* 发送消息 */}
          <div className="glass-card p-4">
            <h3 className="font-medium mb-3 flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              发送消息（企业微信）
            </h3>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="输入消息内容..."
                value={message}
                onChange={e => setMessage(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                className="flex-1 px-4 py-2 bg-dark-purple/50 border border-white/10 rounded-lg focus:border-cyber-blue/50 focus:outline-none transition-colors"
              />
              <button 
                onClick={handleSend}
                disabled={!message.trim() || sending}
                className="btn-cyber flex items-center gap-2 disabled:opacity-50"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                发送
              </button>
            </div>
          </div>
          
          {/* 邮件跟进 */}
          <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium flex items-center gap-2">
                <Mail className="w-4 h-4" />
                邮件跟进
              </h3>
              {!showEmailForm && (
                <button
                  onClick={() => setShowEmailForm(true)}
                  className="text-sm text-cyber-blue hover:underline"
                >
                  展开
                </button>
              )}
            </div>
            
            {showEmailForm ? (
              <div className="space-y-3">
                <textarea
                  placeholder="输入自定义邮件内容（留空则使用AI自动生成）..."
                  value={emailContent}
                  onChange={e => setEmailContent(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 bg-dark-purple/50 border border-white/10 rounded-lg focus:border-cyber-blue/50 focus:outline-none transition-colors resize-none"
                />
                <div className="flex items-center justify-between">
                  <span className="text-gray-500 text-xs">
                    {customer.email 
                      ? `将发送至: ${customer.email}` 
                      : '⚠️ 请先添加客户邮箱'}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setShowEmailForm(false)
                        setEmailContent('')
                      }}
                      className="px-4 py-2 text-sm text-gray-400 hover:text-white"
                    >
                      取消
                    </button>
                    <button 
                      onClick={handleSendEmail}
                      disabled={!customer.email || sendingEmail}
                      className="btn-cyber flex items-center gap-2 disabled:opacity-50"
                    >
                      {sendingEmail ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          发送中...
                        </>
                      ) : (
                        <>
                          <Mail className="w-4 h-4" />
                          {emailContent.trim() ? '发送邮件' : 'AI生成并发送'}
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">
                {customer.email 
                  ? '点击展开，使用AI自动生成跟进邮件并发送给客户' 
                  : '请先添加客户邮箱后再使用邮件跟进功能'}
              </p>
            )}
          </div>
          
          {/* 快捷操作 */}
          <div className="flex gap-3">
            <Link 
              href={`/conversations?customer=${customer.id}`}
              className="flex-1 py-3 glass-card hover:border-cyber-blue/50 transition-colors text-center"
            >
              查看对话记录
            </Link>
            <button 
              onClick={async () => {
                try {
                  const res = await fetch(`/api/customers/${customer.id}/mark-high-intent`, {
                    method: 'POST'
                  })
                  if (res.ok) {
                    alert('已标记为高意向客户！')
                    onClose()
                  } else {
                    alert('操作失败，请重试')
                  }
                } catch (error) {
                  alert('操作失败，请检查网络')
                }
              }}
              className="flex-1 py-3 glass-card hover:border-cyber-green/50 hover:text-cyber-green transition-colors text-center"
            >
              标记为高意向
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// 客户行组件
function CustomerRow({ 
  customer,
  onSelect,
  onQuickMessage
}: { 
  customer: Customer
  onSelect: () => void
  onQuickMessage: () => void
}) {
  const isHighIntent = customer.intentLevel === 'S' || customer.intentLevel === 'A'
  const [showMenu, setShowMenu] = useState(false)
  
  return (
    <motion.tr 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors ${
        isHighIntent ? 'bg-cyber-green/5' : ''
      }`}
    >
      <td className="p-4" onClick={onSelect}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-dark-purple to-cyber-blue/30 flex items-center justify-center font-medium">
            {customer.name?.[0] || '?'}
          </div>
          <div>
            <p className="font-medium">{customer.name || '未知客户'}</p>
            <p className="text-gray-500 text-sm">{customer.company || '-'}</p>
          </div>
        </div>
      </td>
      <td className="p-4" onClick={onSelect}>
        <IntentBadge level={customer.intentLevel} />
      </td>
      <td className="p-4" onClick={onSelect}>
        <span className="font-number text-cyber-blue">{customer.intentScore}</span>
      </td>
      <td className="p-4 text-gray-400" onClick={onSelect}>
        {customer.phone || '-'}
      </td>
      <td className="p-4 text-gray-400" onClick={onSelect}>
        {customer.source}
      </td>
      <td className="p-4 text-gray-500 text-sm" onClick={onSelect}>
        {customer.lastContact || '从未联系'}
      </td>
      <td className="p-4">
        <div className="flex items-center gap-2">
          <button 
            onClick={(e) => {
              e.stopPropagation()
              if (customer.phone) {
                window.open(`tel:${customer.phone}`)
              } else {
                alert('该客户没有电话号码')
              }
            }}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="拨打电话"
          >
            <Phone className="w-4 h-4 text-gray-400" />
          </button>
          <button 
            onClick={(e) => {
              e.stopPropagation()
              onQuickMessage()
            }}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="发送消息"
          >
            <MessageSquare className="w-4 h-4 text-gray-400" />
          </button>
          <div className="relative">
            <button 
              onClick={(e) => {
                e.stopPropagation()
                setShowMenu(!showMenu)
              }}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <MoreVertical className="w-4 h-4 text-gray-400" />
            </button>
            {showMenu && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute right-0 top-full mt-1 w-40 glass-card py-2 z-10"
              >
                <button 
                  onClick={(e) => {
                    e.stopPropagation()
                    onSelect()
                    setShowMenu(false)
                  }}
                  className="w-full px-4 py-2 text-left hover:bg-white/10 transition-colors text-sm"
                >
                  查看详情
                </button>
                <Link 
                  href={`/conversations?customer=${customer.id}`}
                  className="block w-full px-4 py-2 text-left hover:bg-white/10 transition-colors text-sm"
                >
                  对话记录
                </Link>
                <button 
                  onClick={async (e) => {
                    e.stopPropagation()
                    if (!confirm('确定要删除这个客户吗？')) {
                      setShowMenu(false)
                      return
                    }
                    try {
                      const res = await fetch(`/api/customers/${customer.id}`, {
                        method: 'DELETE'
                      })
                      if (res.ok) {
                        alert('客户已删除')
                        window.location.reload()
                      } else {
                        alert('删除失败，请重试')
                      }
                    } catch (error) {
                      alert('删除失败，请检查网络')
                    }
                    setShowMenu(false)
                  }}
                  className="w-full px-4 py-2 text-left hover:bg-white/10 transition-colors text-sm text-alert-red"
                >
                  删除客户
                </button>
              </motion.div>
            )}
          </div>
        </div>
      </td>
    </motion.tr>
  )
}

export default function CustomersPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterLevel, setFilterLevel] = useState<string | null>(null)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  
  // 从API获取真实数据
  const fetchCustomers = async () => {
    try {
      const params = new URLSearchParams()
      if (filterLevel) params.append('intent_level', filterLevel)
      if (searchQuery) params.append('search', searchQuery)
      
      const res = await fetch(`/api/customers?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        if (data.items && data.items.length > 0) {
          const mapped = data.items.map((c: any) => ({
            id: c.id,
            name: c.name || '未知客户',
            company: c.company,
            intentLevel: c.intent_level?.toUpperCase() || 'C',
            intentScore: c.intent_score || 0,
            phone: c.phone,
            email: c.email,
            source: c.source || '微信',
            lastContact: c.last_contact_at ? formatTime(c.last_contact_at) : null,
            createdAt: c.created_at ? formatTime(c.created_at) : null,
            language: c.language || 'auto'
          }))
          setCustomers(mapped)
          setTotal(data.total || mapped.length)
        } else {
          setCustomers([])
          setTotal(0)
        }
      }
    } catch (error) {
      console.error('获取客户列表失败:', error)
      setCustomers([])
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => {
    setLoading(true)
    fetchCustomers()
    const interval = setInterval(fetchCustomers, 30000)
    return () => clearInterval(interval)
  }, [filterLevel, searchQuery])
  
  // 格式化时间
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    if (diff < 604800) return `${Math.floor(diff / 86400)}天前`
    return date.toLocaleDateString('zh-CN')
  }
  
  // 发送消息
  const handleSendMessage = async (customerId: string, message: string) => {
    try {
      const res = await fetch('/api/wechat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id: customerId, content: message })
      })
      if (res.ok) {
        alert('消息发送成功！')
      } else {
        alert('发送失败，请检查企业微信配置')
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      alert('发送失败，请稍后重试')
    }
  }
  
  // 查看高意向客户
  const showHighIntent = () => {
    setFilterLevel('S')
  }
  
  return (
    <div className="min-h-screen p-6">
      {/* 头部 */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">客户管理</h1>
            <p className="text-gray-400 text-sm">共 {total} 位客户 {loading && <Loader2 className="inline w-4 h-4 animate-spin ml-2" />}</p>
          </div>
        </div>
        <button 
          onClick={showHighIntent}
          className="btn-cyber flex items-center gap-2"
        >
          <TrendingUp className="w-4 h-4" />
          查看高意向
        </button>
      </header>
      
      {/* 搜索和筛选 */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="搜索客户名称、公司..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-dark-purple/50 border border-white/10 rounded-lg focus:border-cyber-blue/50 focus:outline-none transition-colors"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setFilterLevel(null)}
            className={`px-3 py-2 rounded-lg transition-colors ${
              !filterLevel 
                ? 'bg-cyber-blue text-black' 
                : 'glass-card hover:border-cyber-blue/50'
            }`}
          >
            全部
          </button>
          {['S', 'A', 'B', 'C'].map((level) => (
            <button
              key={level}
              onClick={() => setFilterLevel(filterLevel === level ? null : level)}
              className={`px-3 py-2 rounded-lg transition-colors ${
                filterLevel === level 
                  ? 'bg-cyber-blue text-black' 
                  : 'glass-card hover:border-cyber-blue/50'
              }`}
            >
              {level}级
            </button>
          ))}
        </div>
      </div>
      
      {/* 客户表格 */}
      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10 text-left">
              <th className="p-4 text-gray-400 font-medium">客户</th>
              <th className="p-4 text-gray-400 font-medium">意向等级</th>
              <th className="p-4 text-gray-400 font-medium">分数</th>
              <th className="p-4 text-gray-400 font-medium">电话</th>
              <th className="p-4 text-gray-400 font-medium">来源</th>
              <th className="p-4 text-gray-400 font-medium">最近联系</th>
              <th className="p-4 text-gray-400 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((customer) => (
              <CustomerRow 
                key={customer.id} 
                customer={customer}
                onSelect={() => setSelectedCustomer(customer)}
                onQuickMessage={() => setSelectedCustomer(customer)}
              />
            ))}
          </tbody>
        </table>
        
        {loading ? (
          <div className="text-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-cyber-blue mx-auto mb-4" />
            <p className="text-gray-500">加载客户数据...</p>
          </div>
        ) : customers.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-400 mb-2">暂无客户数据</p>
            <p className="text-gray-500 text-sm">当客户通过企业微信联系你时，客户记录会自动创建</p>
          </div>
        ) : null}
      </div>
      
      {/* 客户详情弹窗 */}
      <AnimatePresence>
        {selectedCustomer && (
          <CustomerDetailModal 
            customer={selectedCustomer}
            onClose={() => setSelectedCustomer(null)}
            onSendMessage={handleSendMessage}
            onRefresh={fetchCustomers}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
