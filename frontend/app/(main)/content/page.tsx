'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Calendar, 
  Play, 
  Copy, 
  Check, 
  X, 
  RefreshCw, 
  Loader2,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  MessageSquare,
  Video,
  FileText,
  Users,
  TrendingUp,
  Clock,
  Eye,
  Heart,
  Share2,
  Target
} from 'lucide-react'
import Link from 'next/link'

// 平台图标和颜色
const platformConfig: Record<string, { icon: any; color: string; name: string }> = {
  douyin: { icon: Video, color: 'text-pink-500 bg-pink-500/10', name: '抖音' },
  xiaohongshu: { icon: FileText, color: 'text-red-500 bg-red-500/10', name: '小红书' },
  wechat_article: { icon: FileText, color: 'text-green-500 bg-green-500/10', name: '公众号' },
  wechat_moments: { icon: Users, color: 'text-green-400 bg-green-400/10', name: '朋友圈' },
  video_account: { icon: Video, color: 'text-blue-500 bg-blue-500/10', name: '视频号' }
}

// 内容类型配置
const contentTypeConfig: Record<string, { emoji: string; name: string; color: string }> = {
  knowledge: { emoji: '📚', name: '物流知识', color: 'text-blue-400' },
  pricing: { emoji: '💰', name: '运价播报', color: 'text-yellow-400' },
  case: { emoji: '✅', name: '成功案例', color: 'text-green-400' },
  policy: { emoji: '📢', name: '政策解读', color: 'text-orange-400' },
  faq: { emoji: '❓', name: '热门问答', color: 'text-purple-400' },
  story: { emoji: '🏢', name: '公司故事', color: 'text-cyan-400' },
  weekly: { emoji: '📊', name: '周报总结', color: 'text-pink-400' }
}

// 状态配置
const statusConfig: Record<string, { color: string; name: string }> = {
  pending: { color: 'text-gray-400 bg-gray-400/10', name: '待生成' },
  generating: { color: 'text-yellow-400 bg-yellow-400/10', name: '生成中' },
  generated: { color: 'text-green-400 bg-green-400/10', name: '已生成' },
  published: { color: 'text-blue-400 bg-blue-400/10', name: '已发布' },
  failed: { color: 'text-red-400 bg-red-400/10', name: '失败' },
  draft: { color: 'text-gray-400 bg-gray-400/10', name: '草稿' },
  approved: { color: 'text-green-400 bg-green-400/10', name: '已审核' },
  rejected: { color: 'text-red-400 bg-red-400/10', name: '已驳回' }
}

interface CalendarItem {
  id: string
  content_date: string
  day_of_week: number
  content_type: string
  content_name: string
  emoji: string
  status: string
  item_count: number
}

interface ContentItem {
  id: string
  platform: string
  platform_name: string
  title: string | null
  content: string
  hashtags: string[]
  call_to_action: string | null
  video_script: string | null
  status: string
  stats: {
    views: number
    likes: number
    comments: number
    shares: number
    leads: number
  }
}

// 内容详情弹窗
function ContentDetailModal({ 
  calendarId, 
  onClose 
}: { 
  calendarId: string
  onClose: () => void 
}) {
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<ContentItem[]>([])
  const [calendarInfo, setCalendarInfo] = useState<any>(null)
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  useEffect(() => {
    fetchDetail()
  }, [calendarId])

  const fetchDetail = async () => {
    try {
      const res = await fetch(`/api/content/calendar/${calendarId}`)
      if (res.ok) {
        const data = await res.json()
        setItems(data.items || [])
        setCalendarInfo(data)
        if (data.items?.length > 0) {
          setSelectedPlatform(data.items[0].platform)
        }
      }
    } catch (error) {
      console.error('获取内容详情失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async (item: ContentItem) => {
    try {
      const res = await fetch(`/api/content/items/${item.id}/copy`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        await navigator.clipboard.writeText(data.content)
        setCopiedId(item.id)
        setTimeout(() => setCopiedId(null), 2000)
      }
    } catch (error) {
      console.error('复制失败:', error)
    }
  }

  const selectedItem = items.find(i => i.platform === selectedPlatform)

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 20 }}
        className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-5xl max-h-[85vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            {calendarInfo && (
              <>
                <span className="text-3xl">{contentTypeConfig[calendarInfo.content_type]?.emoji}</span>
                <div>
                  <h2 className="text-xl font-bold text-white">
                    {calendarInfo.content_date} - {contentTypeConfig[calendarInfo.content_type]?.name}
                  </h2>
                  <p className="text-gray-400 text-sm">
                    共 {items.length} 个平台内容
                  </p>
                </div>
              </>
            )}
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-10 h-10 animate-spin text-cyan-500" />
          </div>
        ) : (
          <div className="flex h-[calc(85vh-100px)]">
            {/* 左侧平台列表 */}
            <div className="w-48 border-r border-white/10 p-4 space-y-2">
              {items.map(item => {
                const config = platformConfig[item.platform]
                const Icon = config?.icon || FileText
                return (
                  <button
                    key={item.platform}
                    onClick={() => setSelectedPlatform(item.platform)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                      selectedPlatform === item.platform
                        ? 'bg-cyan-500/20 text-cyan-400'
                        : 'hover:bg-white/5 text-gray-400'
                    }`}
                  >
                    <div className={`p-1.5 rounded ${config?.color || 'bg-gray-500/10'}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-sm">{item.platform_name}</span>
                  </button>
                )
              })}
            </div>

            {/* 右侧内容详情 */}
            <div className="flex-1 overflow-y-auto p-6">
              {selectedItem && (
                <div className="space-y-6">
                  {/* 操作按钮 */}
                  <div className="flex items-center justify-between">
                    <span className={`px-3 py-1 rounded-full text-sm ${statusConfig[selectedItem.status]?.color}`}>
                      {statusConfig[selectedItem.status]?.name}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleCopy(selectedItem)}
                        className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-colors"
                      >
                        {copiedId === selectedItem.id ? (
                          <>
                            <Check className="w-4 h-4" />
                            已复制
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4" />
                            复制文案
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* 标题 */}
                  {selectedItem.title && (
                    <div>
                      <label className="text-gray-400 text-sm mb-2 block">标题</label>
                      <div className="bg-white/5 rounded-lg p-4 text-white">
                        {selectedItem.title}
                      </div>
                    </div>
                  )}

                  {/* 正文 */}
                  <div>
                    <label className="text-gray-400 text-sm mb-2 block">正文内容</label>
                    <div className="bg-white/5 rounded-lg p-4 text-white whitespace-pre-wrap max-h-64 overflow-y-auto">
                      {selectedItem.content}
                    </div>
                  </div>

                  {/* 视频脚本（仅抖音） */}
                  {selectedItem.video_script && (
                    <div>
                      <label className="text-gray-400 text-sm mb-2 block">📹 视频脚本</label>
                      <div className="bg-white/5 rounded-lg p-4 text-white whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {selectedItem.video_script}
                      </div>
                    </div>
                  )}

                  {/* 话题标签 */}
                  {selectedItem.hashtags && selectedItem.hashtags.length > 0 && (
                    <div>
                      <label className="text-gray-400 text-sm mb-2 block">话题标签</label>
                      <div className="flex flex-wrap gap-2">
                        {selectedItem.hashtags.map((tag, i) => (
                          <span key={i} className="px-3 py-1 bg-cyan-500/20 text-cyan-400 rounded-full text-sm">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* CTA */}
                  {selectedItem.call_to_action && (
                    <div>
                      <label className="text-gray-400 text-sm mb-2 block">行动号召</label>
                      <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 text-green-400">
                        {selectedItem.call_to_action}
                      </div>
                    </div>
                  )}

                  {/* 数据统计 */}
                  <div>
                    <label className="text-gray-400 text-sm mb-2 block">效果数据</label>
                    <div className="grid grid-cols-5 gap-3">
                      {[
                        { icon: Eye, label: '浏览', value: selectedItem.stats.views },
                        { icon: Heart, label: '点赞', value: selectedItem.stats.likes },
                        { icon: MessageSquare, label: '评论', value: selectedItem.stats.comments },
                        { icon: Share2, label: '分享', value: selectedItem.stats.shares },
                        { icon: Target, label: '线索', value: selectedItem.stats.leads }
                      ].map((stat, i) => (
                        <div key={i} className="bg-white/5 rounded-lg p-3 text-center">
                          <stat.icon className="w-4 h-4 text-gray-400 mx-auto mb-1" />
                          <p className="text-lg font-bold text-white">{stat.value}</p>
                          <p className="text-xs text-gray-500">{stat.label}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}

// 日历卡片
function CalendarCard({ item, onClick }: { item: CalendarItem; onClick: () => void }) {
  const typeConfig = contentTypeConfig[item.content_type] || { emoji: '📝', name: '内容', color: 'text-gray-400' }
  const status = statusConfig[item.status] || statusConfig.pending
  
  const isToday = item.content_date === new Date().toISOString().split('T')[0]
  const isFuture = new Date(item.content_date) > new Date()

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      onClick={onClick}
      className={`p-4 rounded-xl cursor-pointer transition-all border ${
        isToday 
          ? 'bg-cyan-500/10 border-cyan-500/30' 
          : isFuture
            ? 'bg-white/5 border-white/10 hover:border-cyan-500/30'
            : 'bg-white/5 border-white/5 hover:border-white/20'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-2xl">{typeConfig.emoji}</span>
        <span className={`px-2 py-0.5 rounded-full text-xs ${status.color}`}>
          {status.name}
        </span>
      </div>
      
      <div className="mb-2">
        <p className={`font-medium ${typeConfig.color}`}>{typeConfig.name}</p>
        <p className="text-gray-500 text-sm">{item.content_date}</p>
      </div>

      {item.item_count > 0 && (
        <div className="flex items-center gap-1 text-gray-400 text-xs">
          <FileText className="w-3 h-3" />
          <span>{item.item_count} 个平台</span>
        </div>
      )}
    </motion.div>
  )
}

export default function ContentPage() {
  const [calendar, setCalendar] = useState<CalendarItem[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [selectedCalendarId, setSelectedCalendarId] = useState<string | null>(null)
  const [stats, setStats] = useState<any>(null)
  
  // 日期范围
  const [dateRange, setDateRange] = useState(() => {
    const today = new Date()
    const start = new Date(today)
    start.setDate(start.getDate() - 3)
    const end = new Date(today)
    end.setDate(end.getDate() + 10)
    return { start, end }
  })

  const fetchCalendar = useCallback(async () => {
    try {
      const startStr = dateRange.start.toISOString().split('T')[0]
      const endStr = dateRange.end.toISOString().split('T')[0]
      
      const res = await fetch(`/api/content/calendar?start_date=${startStr}&end_date=${endStr}`)
      if (res.ok) {
        const data = await res.json()
        setCalendar(data.items || [])
        setStats(data.stats)
      }
    } catch (error) {
      console.error('获取内容日历失败:', error)
    } finally {
      setLoading(false)
    }
  }, [dateRange])

  useEffect(() => {
    setLoading(true)
    fetchCalendar()
  }, [fetchCalendar])

  // 生成内容
  const handleGenerate = async (days: number = 7) => {
    setGenerating(true)
    try {
      const res = await fetch(`/api/content/generate/batch?days=${days}`, {
        method: 'POST'
      })
      if (res.ok) {
        alert(`已启动未来 ${days} 天的内容生成任务！`)
        // 延迟刷新
        setTimeout(() => {
          fetchCalendar()
          setGenerating(false)
        }, 3000)
      } else {
        const error = await res.json()
        alert(error.detail || '生成失败')
        setGenerating(false)
      }
    } catch (error) {
      console.error('生成失败:', error)
      alert('生成失败，请重试')
      setGenerating(false)
    }
  }

  // 切换日期范围
  const shiftDateRange = (days: number) => {
    setDateRange(prev => ({
      start: new Date(prev.start.getTime() + days * 24 * 60 * 60 * 1000),
      end: new Date(prev.end.getTime() + days * 24 * 60 * 60 * 1000)
    }))
  }

  // 按日期分组
  const groupedCalendar = calendar.reduce((acc, item) => {
    const date = item.content_date
    if (!acc[date]) acc[date] = []
    acc[date].push(item)
    return acc
  }, {} as Record<string, CalendarItem[]>)

  // 生成日期列表
  const dateList: string[] = []
  const current = new Date(dateRange.start)
  while (current <= dateRange.end) {
    dateList.push(current.toISOString().split('T')[0])
    current.setDate(current.getDate() + 1)
  }

  return (
    <div className="min-h-screen p-6 bg-[#0a0a1a]">
      {/* 头部 */}
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="text-3xl">📱</span>
            <span className="bg-gradient-to-r from-cyan-400 to-pink-500 bg-clip-text text-transparent">
              内容工作台
            </span>
          </h1>
          <p className="text-gray-400 mt-1">
            小媒每日自动生成多平台营销内容，让客户主动找你
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchCalendar()}
            disabled={loading}
            className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-5 h-5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => handleGenerate(7)}
            disabled={generating}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-pink-500 rounded-lg text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            {generating ? '生成中...' : '生成未来7天内容'}
          </button>
        </div>
      </header>

      {/* 统计卡片 */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: '待生成', value: stats?.pending || 0, color: 'text-gray-400', icon: Clock },
          { label: '已生成', value: stats?.generated || 0, color: 'text-green-400', icon: Check },
          { label: '已发布', value: stats?.published || 0, color: 'text-cyan-400', icon: Share2 },
          { label: '总内容', value: stats?.total || 0, color: 'text-pink-400', icon: FileText }
        ].map((stat, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="bg-white/5 rounded-xl p-5 border border-white/5"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className={`p-2 rounded-lg ${stat.color} bg-current/10`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <span className="text-gray-400">{stat.label}</span>
            </div>
            <p className={`text-3xl font-bold ${stat.color}`}>{stat.value}</p>
          </motion.div>
        ))}
      </div>

      {/* 日期导航 */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => shiftDateRange(-7)}
          className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
        >
          <ChevronLeft className="w-5 h-5 text-gray-400" />
        </button>
        <div className="text-center">
          <p className="text-gray-400">
            {dateRange.start.toLocaleDateString('zh-CN')} - {dateRange.end.toLocaleDateString('zh-CN')}
          </p>
        </div>
        <button
          onClick={() => shiftDateRange(7)}
          className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
        >
          <ChevronRight className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      {/* 内容日历 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-10 h-10 animate-spin text-cyan-500" />
        </div>
      ) : (
        <div className="grid grid-cols-7 gap-4">
          {/* 星期标题 */}
          {['周一', '周二', '周三', '周四', '周五', '周六', '周日'].map((day, i) => (
            <div key={i} className="text-center text-gray-500 text-sm py-2">
              {day}
            </div>
          ))}

          {/* 日期格子 */}
          {dateList.map(dateStr => {
            const items = groupedCalendar[dateStr] || []
            const dateObj = new Date(dateStr)
            const isToday = dateStr === new Date().toISOString().split('T')[0]
            const dayOfWeek = dateObj.getDay()
            const isWeekend = dayOfWeek === 0 || dayOfWeek === 6

            return (
              <div
                key={dateStr}
                className={`min-h-[120px] rounded-xl p-3 ${
                  isToday 
                    ? 'bg-cyan-500/10 border-2 border-cyan-500/30' 
                    : isWeekend
                      ? 'bg-purple-500/5 border border-white/5'
                      : 'bg-white/5 border border-white/5'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm font-medium ${isToday ? 'text-cyan-400' : 'text-gray-400'}`}>
                    {dateObj.getDate()}日
                  </span>
                  {isToday && (
                    <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded text-xs">
                      今天
                    </span>
                  )}
                </div>

                {items.length > 0 ? (
                  <div className="space-y-2">
                    {items.map(item => (
                      <CalendarCard
                        key={item.id}
                        item={item}
                        onClick={() => setSelectedCalendarId(item.id)}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-16 text-gray-600 text-sm">
                    暂无内容
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* 内容类型图例 */}
      <div className="mt-8 p-4 bg-white/5 rounded-xl">
        <h3 className="text-gray-400 text-sm mb-3">每日内容类型</h3>
        <div className="flex flex-wrap gap-4">
          {Object.entries(contentTypeConfig).map(([key, config]) => (
            <div key={key} className="flex items-center gap-2">
              <span>{config.emoji}</span>
              <span className={`text-sm ${config.color}`}>{config.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 使用说明 */}
      <div className="mt-6 p-4 bg-gradient-to-r from-cyan-500/10 to-pink-500/10 border border-cyan-500/20 rounded-xl">
        <h3 className="text-cyan-400 font-medium mb-2">💡 使用说明</h3>
        <ul className="text-gray-400 text-sm space-y-1">
          <li>• 点击「生成未来7天内容」，小媒会自动为你创建多平台营销内容</li>
          <li>• 点击日历中的内容卡片，可以查看和复制各平台的文案</li>
          <li>• 复制后可直接发布到抖音、小红书、公众号、朋友圈</li>
          <li>• 内容会根据你的公司配置和ERP数据自动生成，贴合实际业务</li>
        </ul>
      </div>

      {/* 内容详情弹窗 */}
      <AnimatePresence>
        {selectedCalendarId && (
          <ContentDetailModal
            calendarId={selectedCalendarId}
            onClose={() => setSelectedCalendarId(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
