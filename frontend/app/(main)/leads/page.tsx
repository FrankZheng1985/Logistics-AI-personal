'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  ArrowLeft,
  Search,
  Target,
  Loader2,
  RefreshCw,
  Globe,
  Phone,
  Mail,
  Building2,
  User,
  MessageCircle,
  ExternalLink,
  Filter,
  TrendingUp,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Zap,
  Play,
  Pause,
  BarChart3
} from 'lucide-react'
import Link from 'next/link'

// 线索类型定义
interface Lead {
  id: string
  name: string | null
  company: string | null
  phone: string | null
  email: string | null
  wechat: string | null
  source: string
  status: string
  intent_level: string
  intent_score: number
  ai_summary: string | null
  needs: string[]
  tags: string[]
  created_at: string
}

interface LeadStats {
  total: number
  today: number
  by_status: Record<string, number>
  by_intent: Record<string, number>
  by_source: Record<string, number>
}

// 搜索配置
interface SearchConfig {
  keywords: string[]
  sources: string[]
  autoSearch: boolean
  interval: number // 分钟
}

// 意向等级颜色
const intentColors: Record<string, string> = {
  high: 'text-cyber-green bg-cyber-green/20 border-cyber-green/30',
  medium: 'text-energy-orange bg-energy-orange/20 border-energy-orange/30',
  low: 'text-gray-400 bg-gray-400/20 border-gray-400/30',
  unknown: 'text-gray-500 bg-gray-500/20 border-gray-500/30'
}

// 状态颜色
const statusColors: Record<string, string> = {
  new: 'text-cyber-blue bg-cyber-blue/20',
  contacted: 'text-energy-orange bg-energy-orange/20',
  qualified: 'text-cyber-green bg-cyber-green/20',
  converted: 'text-neon-purple bg-neon-purple/20',
  invalid: 'text-gray-500 bg-gray-500/20'
}

// 状态名称
const statusNames: Record<string, string> = {
  new: '新线索',
  contacted: '已联系',
  qualified: '已确认',
  converted: '已转化',
  invalid: '无效'
}

// 来源名称
const sourceNames: Record<string, string> = {
  google: 'Google搜索',
  weibo: '微博',
  zhihu: '知乎',
  tieba: '贴吧',
  wechat: '微信',
  manual: '手动添加',
  other: '其他'
}

// 统计卡片组件
function StatsCards({ stats, loading }: { stats: LeadStats | null; loading: boolean }) {
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-4 text-center"
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          <Target className="w-5 h-5 text-cyber-blue" />
          <span className="text-gray-400">总线索</span>
        </div>
        {loading ? (
          <Loader2 className="w-8 h-8 animate-spin text-cyber-blue mx-auto" />
        ) : (
          <p className="text-3xl font-number font-bold text-cyber-blue">{stats?.total || 0}</p>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-card p-4 text-center"
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          <Zap className="w-5 h-5 text-cyber-green" />
          <span className="text-gray-400">今日新增</span>
        </div>
        {loading ? (
          <Loader2 className="w-8 h-8 animate-spin text-cyber-green mx-auto" />
        ) : (
          <p className="text-3xl font-number font-bold text-cyber-green">{stats?.today || 0}</p>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-4 text-center"
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          <TrendingUp className="w-5 h-5 text-energy-orange" />
          <span className="text-gray-400">高意向</span>
        </div>
        {loading ? (
          <Loader2 className="w-8 h-8 animate-spin text-energy-orange mx-auto" />
        ) : (
          <p className="text-3xl font-number font-bold text-energy-orange">
            {stats?.by_intent?.high || 0}
          </p>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card p-4 text-center"
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          <CheckCircle2 className="w-5 h-5 text-neon-purple" />
          <span className="text-gray-400">已转化</span>
        </div>
        {loading ? (
          <Loader2 className="w-8 h-8 animate-spin text-neon-purple mx-auto" />
        ) : (
          <p className="text-3xl font-number font-bold text-neon-purple">
            {stats?.by_status?.converted || 0}
          </p>
        )}
      </motion.div>
    </div>
  )
}

// 搜索控制面板
function SearchPanel({ 
  onSearch, 
  isSearching,
  lastSearchTime 
}: { 
  onSearch: () => void
  isSearching: boolean
  lastSearchTime: string | null
}) {
  const [keywords, setKeywords] = useState('找货代, 物流报价, FBA物流, 跨境物流')
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6 mb-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center">
            <Target className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold">小猎 - 线索狩猎</h2>
            <p className="text-gray-400 text-sm">自动搜索互联网上的潜在客户线索</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          {lastSearchTime && (
            <>
              <Clock className="w-4 h-4" />
              <span>上次搜索: {lastSearchTime}</span>
            </>
          )}
        </div>
      </div>

      {/* 搜索关键词 */}
      <div className="mb-4">
        <label className="block text-gray-400 text-sm mb-2">搜索关键词（逗号分隔）</label>
        <textarea
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white placeholder-gray-500 focus:border-cyber-blue/50 focus:outline-none resize-none"
          rows={2}
          placeholder="输入搜索关键词..."
        />
      </div>

      {/* 搜索来源 */}
      <div className="mb-4">
        <label className="block text-gray-400 text-sm mb-2">搜索来源</label>
        <div className="flex flex-wrap gap-2">
          {[
            { id: 'google', name: 'Google', icon: Globe },
            { id: 'weibo', name: '微博', icon: MessageCircle },
            { id: 'zhihu', name: '知乎', icon: MessageCircle },
            { id: 'tieba', name: '贴吧', icon: MessageCircle }
          ].map(source => (
            <label
              key={source.id}
              className="flex items-center gap-2 px-3 py-2 glass-card cursor-pointer hover:border-cyber-blue/50 transition-colors"
            >
              <input type="checkbox" defaultChecked className="accent-cyber-blue" />
              <source.icon className="w-4 h-4 text-gray-400" />
              <span className="text-sm">{source.name}</span>
            </label>
          ))}
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-3">
        <button
          onClick={onSearch}
          disabled={isSearching}
          className={`flex-1 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
            isSearching 
              ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-cyber-blue to-neon-purple hover:opacity-90'
          }`}
        >
          {isSearching ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              正在搜索中...
            </>
          ) : (
            <>
              <Search className="w-5 h-5" />
              开始搜索线索
            </>
          )}
        </button>
      </div>

      {/* 搜索说明 */}
      {isSearching && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-4 p-3 bg-cyber-blue/10 border border-cyber-blue/30 rounded-lg"
        >
          <div className="flex items-center gap-2 text-cyber-blue text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>小猎正在互联网上搜索潜在客户，这可能需要1-2分钟...</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

// 线索卡片组件
function LeadCard({ lead, onConvert, onContact }: { 
  lead: Lead
  onConvert: (leadId: string) => void
  onContact: (leadId: string) => void
}) {
  const [converting, setConverting] = useState(false)
  const [contacting, setContacting] = useState(false)
  
  const handleConvert = async () => {
    if (lead.status === 'converted') {
      alert('该线索已转化为客户')
      return
    }
    setConverting(true)
    await onConvert(lead.id)
    setConverting(false)
  }
  
  const handleContact = async () => {
    setContacting(true)
    await onContact(lead.id)
    setContacting(false)
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-4 hover:border-cyber-blue/30 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {/* 头部信息 */}
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyber-blue/50 to-neon-purple/50 flex items-center justify-center">
              {lead.company ? (
                <Building2 className="w-5 h-5 text-white" />
              ) : (
                <User className="w-5 h-5 text-white" />
              )}
            </div>
            <div>
              <h3 className="font-medium">
                {lead.name || lead.company || '未知客户'}
              </h3>
              {lead.company && lead.name && (
                <p className="text-gray-400 text-sm">{lead.company}</p>
              )}
            </div>
          </div>

          {/* 联系方式 */}
          <div className="flex flex-wrap gap-3 mb-3 text-sm">
            {lead.phone && (
              <span className="flex items-center gap-1 text-gray-400">
                <Phone className="w-4 h-4" />
                {lead.phone}
              </span>
            )}
            {lead.email && (
              <span className="flex items-center gap-1 text-gray-400">
                <Mail className="w-4 h-4" />
                {lead.email}
              </span>
            )}
            {lead.wechat && (
              <span className="flex items-center gap-1 text-gray-400">
                <MessageCircle className="w-4 h-4" />
                {lead.wechat}
              </span>
            )}
          </div>

          {/* AI摘要 */}
          {lead.ai_summary && (
            <p className="text-gray-300 text-sm mb-3 line-clamp-2">
              {lead.ai_summary}
            </p>
          )}

          {/* 需求标签 */}
          {lead.needs && lead.needs.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {lead.needs.map((need, index) => (
                <span
                  key={index}
                  className="px-2 py-0.5 bg-cyber-blue/20 text-cyber-blue text-xs rounded"
                >
                  {need}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 右侧状态 */}
        <div className="flex flex-col items-end gap-2">
          <span className={`px-2 py-1 rounded text-xs border ${intentColors[lead.intent_level]}`}>
            {lead.intent_level === 'high' ? '高意向' : 
             lead.intent_level === 'medium' ? '中意向' : 
             lead.intent_level === 'low' ? '低意向' : '待分析'}
          </span>
          <span className={`px-2 py-0.5 rounded text-xs ${statusColors[lead.status]}`}>
            {statusNames[lead.status] || lead.status}
          </span>
          <span className="text-gray-500 text-xs">
            {sourceNames[lead.source] || lead.source}
          </span>
        </div>
      </div>

      {/* 底部操作 */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/10">
        <span className="text-gray-500 text-xs">
          {new Date(lead.created_at).toLocaleString('zh-CN')}
        </span>
        <div className="flex gap-2">
          <button 
            onClick={handleConvert}
            disabled={converting || lead.status === 'converted'}
            className={`px-3 py-1 text-xs glass-card transition-colors flex items-center gap-1 ${
              lead.status === 'converted' 
                ? 'opacity-50 cursor-not-allowed' 
                : 'hover:border-cyber-blue/50'
            }`}
          >
            {converting ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
            {lead.status === 'converted' ? '已转化' : '转为客户'}
          </button>
          <button 
            onClick={handleContact}
            disabled={contacting}
            className="px-3 py-1 text-xs glass-card hover:border-cyber-green/50 transition-colors flex items-center gap-1"
          >
            {contacting ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
            联系
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// 空状态组件
function EmptyState({ onSearch }: { onSearch: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="text-center py-16"
    >
      <div className="w-20 h-20 rounded-full bg-gradient-to-br from-cyber-blue/20 to-neon-purple/20 flex items-center justify-center mx-auto mb-4">
        <Target className="w-10 h-10 text-gray-400" />
      </div>
      <h3 className="text-xl font-medium mb-2">还没有线索</h3>
      <p className="text-gray-400 mb-6">
        点击上方「开始搜索线索」让小猎为您寻找潜在客户
      </p>
      <button
        onClick={onSearch}
        className="px-6 py-3 bg-gradient-to-r from-cyber-blue to-neon-purple rounded-lg font-medium hover:opacity-90 transition-opacity"
      >
        <Search className="w-5 h-5 inline mr-2" />
        立即开始搜索
      </button>
    </motion.div>
  )
}

// 主页面组件
export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [stats, setStats] = useState<LeadStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [isSearching, setIsSearching] = useState(false)
  const [lastSearchTime, setLastSearchTime] = useState<string | null>(null)
  const [filter, setFilter] = useState({
    status: '',
    intent_level: '',
    source: ''
  })

  // 加载线索列表
  const fetchLeads = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (filter.status) params.append('status', filter.status)
      if (filter.intent_level) params.append('intent_level', filter.intent_level)
      if (filter.source) params.append('source', filter.source)
      
      const response = await fetch(`/api/leads?${params.toString()}`)
      if (response.ok) {
        const data = await response.json()
        setLeads(data.items || [])
      }
    } catch (error) {
      console.error('获取线索失败:', error)
    }
  }, [filter])

  // 加载统计数据
  const fetchStats = async () => {
    try {
      const response = await fetch('/api/leads/stats')
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('获取统计失败:', error)
    }
  }

  // 初始加载
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([fetchLeads(), fetchStats()])
      setLoading(false)
    }
    loadData()
  }, [fetchLeads])

  // 开始搜索
  const handleSearch = async () => {
    setIsSearching(true)
    try {
      const response = await fetch('/api/leads/hunt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (response.ok) {
        setLastSearchTime(new Date().toLocaleTimeString('zh-CN'))
        
        // 等待一段时间后刷新数据
        setTimeout(async () => {
          await Promise.all([fetchLeads(), fetchStats()])
          setIsSearching(false)
        }, 5000)
      } else {
        setIsSearching(false)
        alert('搜索启动失败，请重试')
      }
    } catch (error) {
      console.error('搜索失败:', error)
      setIsSearching(false)
      alert('搜索失败，请检查网络连接')
    }
  }

  // 转化线索为客户
  const handleConvertLead = async (leadId: string) => {
    try {
      const response = await fetch(`/api/leads/${leadId}/convert`, {
        method: 'POST'
      })
      
      if (response.ok) {
        const data = await response.json()
        alert(`转化成功！客户ID: ${data.customer_id.slice(0, 8)}...`)
        // 刷新列表
        await Promise.all([fetchLeads(), fetchStats()])
      } else {
        const error = await response.json()
        alert(error.detail || '转化失败，请重试')
      }
    } catch (error) {
      console.error('转化失败:', error)
      alert('转化失败，请检查网络连接')
    }
  }

  // 联系线索
  const handleContactLead = async (leadId: string) => {
    try {
      const response = await fetch(`/api/leads/${leadId}/contact`, {
        method: 'POST'
      })
      
      if (response.ok) {
        const data = await response.json()
        alert(`联系记录已更新，这是第 ${data.contact_count} 次联系`)
        // 刷新列表
        await fetchLeads()
      } else {
        const error = await response.json()
        alert(error.detail || '更新失败，请重试')
      }
    } catch (error) {
      console.error('联系失败:', error)
      alert('操作失败，请检查网络连接')
    }
  }

  return (
    <div className="min-h-screen p-6">
      {/* 头部 */}
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
                线索狩猎
              </span>
            </h1>
            <p className="text-gray-400 text-sm">让小猎为您自动发现潜在客户</p>
          </div>
        </div>
        <button
          onClick={() => {
            setLoading(true)
            Promise.all([fetchLeads(), fetchStats()]).then(() => setLoading(false))
          }}
          className="p-2 glass-card hover:border-cyber-blue/50 transition-colors"
        >
          <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </header>

      {/* 统计卡片 */}
      <StatsCards stats={stats} loading={loading} />

      {/* 搜索控制面板 */}
      <SearchPanel 
        onSearch={handleSearch}
        isSearching={isSearching}
        lastSearchTime={lastSearchTime}
      />

      {/* 过滤器 */}
      <div className="flex gap-3 mb-6">
        <select
          value={filter.status}
          onChange={(e) => setFilter(prev => ({ ...prev, status: e.target.value }))}
          className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-cyber-blue/50 focus:outline-none"
        >
          <option value="">所有状态</option>
          <option value="new">新线索</option>
          <option value="contacted">已联系</option>
          <option value="qualified">已确认</option>
          <option value="converted">已转化</option>
          <option value="invalid">无效</option>
        </select>

        <select
          value={filter.intent_level}
          onChange={(e) => setFilter(prev => ({ ...prev, intent_level: e.target.value }))}
          className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-cyber-blue/50 focus:outline-none"
        >
          <option value="">所有意向</option>
          <option value="high">高意向</option>
          <option value="medium">中意向</option>
          <option value="low">低意向</option>
        </select>

        <select
          value={filter.source}
          onChange={(e) => setFilter(prev => ({ ...prev, source: e.target.value }))}
          className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-cyber-blue/50 focus:outline-none"
        >
          <option value="">所有来源</option>
          <option value="google">Google</option>
          <option value="weibo">微博</option>
          <option value="zhihu">知乎</option>
          <option value="manual">手动添加</option>
        </select>
      </div>

      {/* 线索列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-10 h-10 animate-spin text-cyber-blue" />
        </div>
      ) : leads.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {leads.map((lead) => (
            <LeadCard 
              key={lead.id} 
              lead={lead}
              onConvert={handleConvertLead}
              onContact={handleContactLead}
            />
          ))}
        </div>
      ) : (
        <EmptyState onSearch={handleSearch} />
      )}

      {/* 底部提示 */}
      <div className="mt-8 p-4 glass-card border-cyber-blue/30">
        <p className="text-gray-400 text-sm">
          💡 <strong className="text-cyber-blue">提示：</strong>
          小猎会搜索 Google、微博、知乎、贴吧等平台上的物流需求信息，自动分析并提取潜在客户线索。
          高意向线索建议尽快联系！
        </p>
      </div>
    </div>
  )
}
