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
  BarChart3,
  Ban,
  RotateCcw,
  FileText,
  Copy,
  Check,
  Sparkles,
  MessageSquare,
  Eye,
  SkipForward
} from 'lucide-react'
import Link from 'next/link'

// ==================== 类型定义 ====================

// 线索类型
interface Lead {
  id: string
  name: string | null
  company: string | null
  phone: string | null
  email: string | null
  wechat: string | null
  source: string
  source_url: string | null
  source_content: string | null
  status: string
  intent_level: string
  intent_score: number
  ai_summary: string | null
  needs: string[]
  tags: string[]
  created_at: string
}

// 话题类型
interface Topic {
  id: string
  title: string
  url: string
  platform: string
  category: string
  keywords: string[]
  value_score: number
  ai_summary: string | null
  ai_answer_strategy: string | null
  ai_recommended_points: string[]
  status: string
  priority: string
  generated_content: string | null
  generated_at: string | null
  published_at: string | null
  discovered_at: string | null
}

interface LeadStats {
  total: number
  today: number
  by_status: Record<string, number>
  by_intent: Record<string, number>
  by_source: Record<string, number>
}

interface TopicStats {
  total: number
  new: number
  answered: number
  high_value: number
  today: number
  by_platform: Record<string, number>
}

// ==================== 常量配置 ====================

const intentColors: Record<string, string> = {
  high: 'text-cyber-green bg-cyber-green/20 border-cyber-green/30',
  medium: 'text-energy-orange bg-energy-orange/20 border-energy-orange/30',
  low: 'text-gray-400 bg-gray-400/20 border-gray-400/30',
  unknown: 'text-gray-500 bg-gray-500/20 border-gray-500/30'
}

const statusColors: Record<string, string> = {
  new: 'text-cyber-blue bg-cyber-blue/20',
  contacted: 'text-energy-orange bg-energy-orange/20',
  qualified: 'text-cyber-green bg-cyber-green/20',
  converted: 'text-neon-purple bg-neon-purple/20',
  invalid: 'text-gray-500 bg-gray-500/20',
  answered: 'text-cyber-green bg-cyber-green/20',
  skipped: 'text-gray-500 bg-gray-500/20'
}

const statusNames: Record<string, string> = {
  new: '待处理',
  contacted: '已联系',
  qualified: '已确认',
  converted: '已转化',
  invalid: '已过滤',
  answered: '已回答',
  skipped: '已跳过'
}

const platformNames: Record<string, string> = {
  zhihu: '知乎',
  xiaohongshu: '小红书',
  weibo: '微博',
  douyin: '抖音',
  bilibili: 'B站',
  google: 'Google'
}

const platformColors: Record<string, string> = {
  zhihu: 'text-blue-400 bg-blue-500/20',
  xiaohongshu: 'text-red-400 bg-red-500/20',
  weibo: 'text-orange-400 bg-orange-500/20',
  douyin: 'text-pink-400 bg-pink-500/20'
}

// ==================== 话题卡片组件 ====================

function TopicCard({ 
  topic, 
  onGenerateAnswer,
  onMarkAnswered,
  onSkip,
  isGenerating 
}: { 
  topic: Topic
  onGenerateAnswer: (topicId: string) => Promise<void>
  onMarkAnswered: (topicId: string) => Promise<void>
  onSkip: (topicId: string) => Promise<void>
  isGenerating: boolean
}) {
  const [copied, setCopied] = useState(false)
  const [showContent, setShowContent] = useState(false)
  
  const copyContent = () => {
    if (topic.generated_content) {
      navigator.clipboard.writeText(topic.generated_content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }
  
  const isNew = topic.status === 'new'
  const hasContent = !!topic.generated_content
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass-card p-4 transition-colors ${
        !isNew ? 'opacity-60' : 'hover:border-cyber-blue/30'
      }`}
    >
      {/* 头部 */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2 py-0.5 rounded text-xs ${platformColors[topic.platform] || 'bg-gray-500/20'}`}>
              {platformNames[topic.platform] || topic.platform}
            </span>
            {topic.priority === 'high' && (
              <span className="px-2 py-0.5 rounded text-xs bg-cyber-green/20 text-cyber-green">
                高价值
              </span>
            )}
            <span className={`px-2 py-0.5 rounded text-xs ${statusColors[topic.status]}`}>
              {statusNames[topic.status]}
            </span>
          </div>
          <h3 className="font-medium text-white line-clamp-2 mb-2">
            {topic.title}
          </h3>
        </div>
        <div className="text-right ml-4">
          <div className="text-2xl font-bold text-cyber-blue">{topic.value_score}</div>
          <div className="text-xs text-gray-500">价值分</div>
        </div>
      </div>
      
      {/* AI分析 */}
      {topic.ai_summary && (
        <p className="text-sm text-gray-400 mb-3 line-clamp-2">
          💡 {topic.ai_summary}
        </p>
      )}
      
      {/* 回答策略 */}
      {topic.ai_answer_strategy && (
        <div className="bg-white/5 rounded-lg p-3 mb-3">
          <div className="text-xs text-gray-500 mb-1">📝 回答策略</div>
          <p className="text-sm text-gray-300">{topic.ai_answer_strategy}</p>
        </div>
      )}
      
      {/* 推荐要点 */}
      {topic.ai_recommended_points && topic.ai_recommended_points.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {topic.ai_recommended_points.slice(0, 3).map((point, index) => (
            <span key={index} className="px-2 py-0.5 text-xs bg-neon-purple/20 text-neon-purple rounded">
              {point}
            </span>
          ))}
        </div>
      )}
      
      {/* 已生成的内容 */}
      {hasContent && (
        <div className="mb-3">
          <button
            onClick={() => setShowContent(!showContent)}
            className="flex items-center gap-1 text-xs text-cyber-blue hover:text-cyber-blue/80"
          >
            <Eye className="w-3 h-3" />
            {showContent ? '收起内容' : '查看生成的内容'}
          </button>
          
          {showContent && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-2 p-3 bg-white/5 rounded-lg"
            >
              <pre className="text-sm text-gray-300 whitespace-pre-wrap font-sans">
                {topic.generated_content}
              </pre>
            </motion.div>
          )}
        </div>
      )}
      
      {/* 底部操作 */}
      <div className="flex items-center justify-between pt-3 border-t border-white/10">
        <div className="flex items-center gap-2">
          <a
            href={topic.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-cyber-blue hover:underline"
          >
            <ExternalLink className="w-3 h-3" />
            查看原帖
          </a>
          <span className="text-gray-600">·</span>
          <span className="text-xs text-gray-500">
            {topic.discovered_at ? new Date(topic.discovered_at).toLocaleDateString('zh-CN') : ''}
          </span>
        </div>
        
        <div className="flex gap-2">
          {isNew && (
            <>
              {/* 跳过按钮 */}
              <button
                onClick={() => onSkip(topic.id)}
                className="px-3 py-1 text-xs glass-card hover:border-gray-500/50 transition-colors flex items-center gap-1 text-gray-400"
              >
                <SkipForward className="w-3 h-3" />
                跳过
              </button>
              
              {/* 生成回答按钮 */}
              {!hasContent ? (
                <button
                  onClick={() => onGenerateAnswer(topic.id)}
                  disabled={isGenerating}
                  className="px-3 py-1 text-xs bg-gradient-to-r from-cyber-blue to-neon-purple rounded-lg hover:opacity-90 transition-opacity flex items-center gap-1"
                >
                  {isGenerating ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Sparkles className="w-3 h-3" />
                  )}
                  生成回答
                </button>
              ) : (
                <>
                  {/* 复制内容按钮 */}
                  <button
                    onClick={copyContent}
                    className="px-3 py-1 text-xs glass-card hover:border-cyber-green/50 transition-colors flex items-center gap-1 text-cyber-green"
                  >
                    {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copied ? '已复制' : '复制内容'}
                  </button>
                  
                  {/* 标记已回答 */}
                  <button
                    onClick={() => onMarkAnswered(topic.id)}
                    className="px-3 py-1 text-xs glass-card hover:border-cyber-blue/50 transition-colors flex items-center gap-1"
                  >
                    <CheckCircle2 className="w-3 h-3" />
                    已发布
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// ==================== 话题模式统计卡片 ====================

function TopicStatsCards({ stats, loading }: { stats: TopicStats | null; loading: boolean }) {
  return (
    <div className="stats-grid mb-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-3 md:p-4 text-center"
      >
        <div className="flex items-center justify-center gap-1 md:gap-2 mb-2">
          <MessageSquare className="w-4 h-4 md:w-5 md:h-5 text-cyber-blue" />
          <span className="text-gray-400 text-xs md:text-sm">待回答</span>
        </div>
        {loading ? (
          <Loader2 className="w-6 h-6 md:w-8 md:h-8 animate-spin text-cyber-blue mx-auto" />
        ) : (
          <p className="text-xl md:text-3xl font-number font-bold text-cyber-blue">{stats?.new || 0}</p>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-card p-3 md:p-4 text-center"
      >
        <div className="flex items-center justify-center gap-1 md:gap-2 mb-2">
          <Zap className="w-4 h-4 md:w-5 md:h-5 text-cyber-green" />
          <span className="text-gray-400 text-xs md:text-sm">高价值</span>
        </div>
        {loading ? (
          <Loader2 className="w-6 h-6 md:w-8 md:h-8 animate-spin text-cyber-green mx-auto" />
        ) : (
          <p className="text-xl md:text-3xl font-number font-bold text-cyber-green">{stats?.high_value || 0}</p>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-3 md:p-4 text-center"
      >
        <div className="flex items-center justify-center gap-1 md:gap-2 mb-2">
          <CheckCircle2 className="w-4 h-4 md:w-5 md:h-5 text-neon-purple" />
          <span className="text-gray-400 text-xs md:text-sm">已回答</span>
        </div>
        {loading ? (
          <Loader2 className="w-6 h-6 md:w-8 md:h-8 animate-spin text-neon-purple mx-auto" />
        ) : (
          <p className="text-xl md:text-3xl font-number font-bold text-neon-purple">{stats?.answered || 0}</p>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card p-3 md:p-4 text-center"
      >
        <div className="flex items-center justify-center gap-1 md:gap-2 mb-2">
          <TrendingUp className="w-4 h-4 md:w-5 md:h-5 text-energy-orange" />
          <span className="text-gray-400 text-xs md:text-sm">今日发现</span>
        </div>
        {loading ? (
          <Loader2 className="w-6 h-6 md:w-8 md:h-8 animate-spin text-energy-orange mx-auto" />
        ) : (
          <p className="text-xl md:text-3xl font-number font-bold text-energy-orange">{stats?.today || 0}</p>
        )}
      </motion.div>
    </div>
  )
}

// ==================== 话题发现面板 ====================

function TopicDiscoveryPanel({ 
  onDiscover, 
  isDiscovering,
  lastDiscoverTime 
}: { 
  onDiscover: () => void
  isDiscovering: boolean
  lastDiscoverTime: string | null
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6 mb-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-neon-purple to-cyber-blue flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold">小猎 - 话题发现模式</h2>
            <p className="text-gray-400 text-sm">发现热门话题，让小文生成专业回答，引流获客</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          {lastDiscoverTime && (
            <>
              <Clock className="w-4 h-4" />
              <span>上次发现: {lastDiscoverTime}</span>
            </>
          )}
        </div>
      </div>

      {/* 工作流程说明 */}
      <div className="bg-white/5 rounded-lg p-4 mb-4">
        <div className="grid grid-cols-4 gap-4 text-center">
          <div>
            <div className="w-8 h-8 rounded-full bg-cyber-blue/20 flex items-center justify-center mx-auto mb-2">
              <Search className="w-4 h-4 text-cyber-blue" />
            </div>
            <p className="text-xs text-gray-400">1. 小猎发现话题</p>
          </div>
          <div>
            <div className="w-8 h-8 rounded-full bg-neon-purple/20 flex items-center justify-center mx-auto mb-2">
              <Sparkles className="w-4 h-4 text-neon-purple" />
            </div>
            <p className="text-xs text-gray-400">2. 小文生成回答</p>
          </div>
          <div>
            <div className="w-8 h-8 rounded-full bg-cyber-green/20 flex items-center justify-center mx-auto mb-2">
              <Copy className="w-4 h-4 text-cyber-green" />
            </div>
            <p className="text-xs text-gray-400">3. 复制并发布</p>
          </div>
          <div>
            <div className="w-8 h-8 rounded-full bg-energy-orange/20 flex items-center justify-center mx-auto mb-2">
              <TrendingUp className="w-4 h-4 text-energy-orange" />
            </div>
            <p className="text-xs text-gray-400">4. 客户主动联系</p>
      </div>
        </div>
      </div>

      {/* 操作按钮 */}
        <button
        onClick={onDiscover}
        disabled={isDiscovering}
        className={`w-full py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
          isDiscovering 
              ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
            : 'bg-gradient-to-r from-neon-purple to-cyber-blue hover:opacity-90'
          }`}
        >
        {isDiscovering ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
            正在发现热门话题...
            </>
          ) : (
            <>
              <Search className="w-5 h-5" />
            发现热门话题
            </>
          )}
        </button>

      {isDiscovering && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-4 p-3 bg-neon-purple/10 border border-neon-purple/30 rounded-lg"
        >
          <div className="flex items-center gap-2 text-neon-purple text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>小猎正在知乎、小红书等平台搜索热门话题...</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

// ==================== 主页面组件 ====================

export default function LeadsPage() {
  // 模式切换
  const [mode, setMode] = useState<'topics' | 'leads'>('topics')
  
  // 话题相关状态
  const [topics, setTopics] = useState<Topic[]>([])
  const [topicStats, setTopicStats] = useState<TopicStats | null>(null)
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [lastDiscoverTime, setLastDiscoverTime] = useState<string | null>(null)
  const [generatingTopicId, setGeneratingTopicId] = useState<string | null>(null)
  
  // 线索相关状态（保留原功能）
  const [leads, setLeads] = useState<Lead[]>([])
  const [leadStats, setLeadStats] = useState<LeadStats | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [lastSearchTime, setLastSearchTime] = useState<string | null>(null)
  
  // 通用状态
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({
    status: '',
    platform: ''
  })

  // ==================== 话题相关函数 ====================
  
  const fetchTopics = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (filter.status) params.append('status', filter.status)
      if (filter.platform) params.append('platform', filter.platform)
      
      const response = await fetch(`/api/topics?${params.toString()}`)
      if (response.ok) {
        const data = await response.json()
        setTopics(data.items || [])
      }
    } catch (error) {
      console.error('获取话题失败:', error)
    }
  }, [filter])

  const fetchTopicStats = async () => {
    try {
      const response = await fetch('/api/topics/stats')
      if (response.ok) {
        const data = await response.json()
        setTopicStats(data)
      }
    } catch (error) {
      console.error('获取话题统计失败:', error)
    }
  }
  
  const handleDiscoverTopics = async () => {
    setIsDiscovering(true)
    try {
      const response = await fetch('/api/topics/discover', {
        method: 'POST'
      })
      
      if (response.ok) {
        setLastDiscoverTime(new Date().toLocaleTimeString('zh-CN'))
        // 等待一段时间后刷新
        setTimeout(async () => {
          await Promise.all([fetchTopics(), fetchTopicStats()])
          setIsDiscovering(false)
        }, 8000)
      } else {
        setIsDiscovering(false)
        const error = await response.json()
        alert(error.detail || '发现话题失败')
      }
    } catch (error) {
      console.error('发现话题失败:', error)
      setIsDiscovering(false)
      alert('发现话题失败，请检查网络连接')
    }
  }
  
  const handleGenerateAnswer = async (topicId: string) => {
    setGeneratingTopicId(topicId)
    try {
      const response = await fetch(`/api/topics/${topicId}/generate`, {
        method: 'POST'
      })
      
      if (response.ok) {
        await fetchTopics()
      } else {
        const error = await response.json()
        alert(error.detail || '生成回答失败')
      }
    } catch (error) {
      console.error('生成回答失败:', error)
      alert('生成回答失败，请重试')
    } finally {
      setGeneratingTopicId(null)
    }
  }
  
  const handleMarkAnswered = async (topicId: string) => {
    try {
      await fetch(`/api/topics/${topicId}/mark-answered`, { method: 'POST' })
      await Promise.all([fetchTopics(), fetchTopicStats()])
    } catch (error) {
      console.error('标记失败:', error)
    }
  }
  
  const handleSkipTopic = async (topicId: string) => {
    try {
      await fetch(`/api/topics/${topicId}/skip`, { method: 'POST' })
      await Promise.all([fetchTopics(), fetchTopicStats()])
    } catch (error) {
      console.error('跳过失败:', error)
    }
  }

  // ==================== 初始加载 ====================
  
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      if (mode === 'topics') {
        await Promise.all([fetchTopics(), fetchTopicStats()])
      } else {
        // 加载线索数据（保留原功能）
        try {
          const response = await fetch('/api/leads')
          if (response.ok) {
            const data = await response.json()
            setLeads(data.items || [])
          }
          const statsResponse = await fetch('/api/leads/stats')
          if (statsResponse.ok) {
            const statsData = await statsResponse.json()
            setLeadStats(statsData)
      }
    } catch (error) {
          console.error('加载数据失败:', error)
    }
  }
      setLoading(false)
    }
    loadData()
  }, [mode, fetchTopics])

  return (
    <div className="min-h-screen">
      {/* 头部 */}
      <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3 md:gap-4">
          <Link href="/dashboard" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="page-title text-xl md:text-2xl">
              {mode === 'topics' ? '话题发现' : '线索狩猎'}
            </h1>
            <p className="page-subtitle text-xs md:text-sm">
              {mode === 'topics' 
                ? '发现热门话题，用专业内容引流获客' 
                : '搜索互联网上的潜在客户线索'}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2 md:gap-3">
          {/* 模式切换 */}
          <div className="flex glass-card p-1 flex-1 lg:flex-none">
            <button
              onClick={() => setMode('topics')}
              className={`flex-1 lg:flex-none px-3 md:px-4 py-2 rounded text-xs md:text-sm transition-all flex items-center justify-center gap-1 ${
                mode === 'topics' 
                  ? 'bg-gradient-to-r from-neon-purple to-cyber-blue text-white' 
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-3 h-3 md:w-4 md:h-4" />
              <span className="hidden sm:inline">话题发现</span>
              <span className="sm:hidden">话题</span>
            </button>
            <button
              onClick={() => setMode('leads')}
              className={`flex-1 lg:flex-none px-3 md:px-4 py-2 rounded text-xs md:text-sm transition-all flex items-center justify-center gap-1 ${
                mode === 'leads' 
                  ? 'bg-gradient-to-r from-cyber-blue to-neon-purple text-white' 
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Target className="w-3 h-3 md:w-4 md:h-4" />
              <span className="hidden sm:inline">线索搜索</span>
              <span className="sm:hidden">线索</span>
            </button>
          </div>
          
          <button
            onClick={async () => {
              setLoading(true)
              if (mode === 'topics') {
                await Promise.all([fetchTopics(), fetchTopicStats()])
              }
              setLoading(false)
            }}
            className="p-2 glass-card hover:border-cyber-blue/50 transition-colors flex-shrink-0"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      {/* 话题发现模式 */}
      {mode === 'topics' && (
        <>
      {/* 统计卡片 */}
          <TopicStatsCards stats={topicStats} loading={loading} />
          
          {/* 发现面板 */}
          <TopicDiscoveryPanel 
            onDiscover={handleDiscoverTopics}
            isDiscovering={isDiscovering}
            lastDiscoverTime={lastDiscoverTime}
          />
          
          {/* 筛选器 */}
      <div className="flex flex-wrap gap-3 mb-6 items-center">
        <select
          value={filter.status}
          onChange={(e) => setFilter(prev => ({ ...prev, status: e.target.value }))}
          className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-cyber-blue/50 focus:outline-none"
        >
          <option value="">所有状态</option>
              <option value="new">待回答</option>
              <option value="answered">已回答</option>
              <option value="skipped">已跳过</option>
        </select>

        <select
              value={filter.platform}
              onChange={(e) => setFilter(prev => ({ ...prev, platform: e.target.value }))}
          className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-cyber-blue/50 focus:outline-none"
        >
              <option value="">所有平台</option>
          <option value="zhihu">知乎</option>
              <option value="xiaohongshu">小红书</option>
        </select>
      </div>

          {/* 话题列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
              <Loader2 className="w-10 h-10 animate-spin text-neon-purple" />
        </div>
          ) : topics.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {topics.map((topic) => (
                <TopicCard 
                  key={topic.id} 
                  topic={topic}
                  onGenerateAnswer={handleGenerateAnswer}
                  onMarkAnswered={handleMarkAnswered}
                  onSkip={handleSkipTopic}
                  isGenerating={generatingTopicId === topic.id}
            />
          ))}
        </div>
      ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-16"
            >
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-neon-purple/20 to-cyber-blue/20 flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-10 h-10 text-gray-400" />
              </div>
              <h3 className="text-xl font-medium mb-2">还没有发现话题</h3>
              <p className="text-gray-400 mb-6">
                点击上方「发现热门话题」让小猎为您寻找值得回答的话题
              </p>
              <button
                onClick={handleDiscoverTopics}
                disabled={isDiscovering}
                className="px-6 py-3 bg-gradient-to-r from-neon-purple to-cyber-blue rounded-lg font-medium hover:opacity-90 transition-opacity"
              >
                <Search className="w-5 h-5 inline mr-2" />
                立即发现话题
              </button>
            </motion.div>
      )}

      {/* 底部提示 */}
          <div className="mt-8 p-4 glass-card border-neon-purple/30">
        <p className="text-gray-400 text-sm">
              💡 <strong className="text-neon-purple">内容引流流程：</strong>
              小猎发现热门话题 → 点击"生成回答"让小文写专业内容 → 复制内容到原帖下回答 → 留下联系方式 → 客户主动找你！
            </p>
          </div>
        </>
      )}

      {/* 线索搜索模式（保留原功能，简化显示） */}
      {mode === 'leads' && (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-cyber-blue/20 to-neon-purple/20 flex items-center justify-center mx-auto mb-4">
            <Target className="w-10 h-10 text-gray-400" />
          </div>
          <h3 className="text-xl font-medium mb-2">线索搜索模式</h3>
          <p className="text-gray-400 mb-6">
            搜索知乎、微博等平台的物流需求帖子
          </p>
          <p className="text-sm text-energy-orange">
            💡 推荐使用「话题发现」模式，通过内容引流获取更高质量的客户
        </p>
      </div>
      )}
    </div>
  )
}
