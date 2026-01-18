'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  ShoppingCart,
  Search,
  Loader2,
  RefreshCw,
  TrendingUp,
  ExternalLink,
  Filter,
  Package,
  Truck,
  Euro,
  BarChart3,
  Mail,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Globe
} from 'lucide-react'

// API基础URL - 生产环境使用相对路径（通过nginx代理）
const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

interface ProductTrend {
  id: string
  product_name: string
  category: string | null
  description: string | null
  source_url: string | null
  source_platform: string | null
  source_region: string
  sales_volume: string | null
  price_range: string | null
  growth_rate: string | null
  trend_score: number
  ai_analysis: string | null
  ai_opportunity: string | null
  ai_logistics_tips: string | null
  keywords: string[]
  status: string
  is_added_to_knowledge: boolean
  is_email_sent: boolean
  discovered_at: string | null
  created_at: string
}

interface ProductStats {
  total: number
  today: number
  high_trend: number
  emailed: number
  by_category: Record<string, number>
  recent_products: Array<{
    name: string
    category: string
    score: number
    url: string
    created_at: string
  }>
}

// 颜色配置
const scoreColors = {
  high: 'text-cyber-green bg-cyber-green/20 border-cyber-green/30',
  medium: 'text-energy-orange bg-energy-orange/20 border-energy-orange/30',
  low: 'text-gray-400 bg-gray-400/20 border-gray-400/30'
}

const platformColors: Record<string, string> = {
  amazon: 'text-orange-400 bg-orange-500/20',
  temu: 'text-pink-400 bg-pink-500/20',
  shein: 'text-purple-400 bg-purple-500/20',
  google: 'text-blue-400 bg-blue-500/20',
  baidu: 'text-red-400 bg-red-500/20'
}

const platformNames: Record<string, string> = {
  amazon: 'Amazon',
  temu: 'Temu',
  shein: 'SHEIN',
  google: 'Google',
  baidu: '百度'
}

// 产品卡片组件
function ProductCard({ product }: { product: ProductTrend }) {
  const [expanded, setExpanded] = useState(false)
  
  const getScoreLevel = (score: number) => {
    if (score >= 70) return 'high'
    if (score >= 50) return 'medium'
    return 'low'
  }
  
  const scoreLevel = getScoreLevel(product.trend_score)
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card overflow-hidden hover:border-cyber-blue/30 transition-colors"
    >
      {/* 头部 */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 rounded text-xs ${platformColors[product.source_platform || ''] || 'bg-gray-500/20 text-gray-400'}`}>
                {platformNames[product.source_platform || ''] || product.source_platform || '未知'}
              </span>
              {product.category && (
                <span className="px-2 py-0.5 rounded text-xs bg-neon-purple/20 text-neon-purple">
                  {product.category}
                </span>
              )}
            </div>
            <h3 className="font-medium text-white line-clamp-2">
              {product.product_name}
            </h3>
          </div>
          
          {/* 趋势评分 */}
          <div className="text-right ml-4">
            <div className={`text-2xl font-bold ${scoreLevel === 'high' ? 'text-cyber-green' : scoreLevel === 'medium' ? 'text-energy-orange' : 'text-gray-400'}`}>
              {product.trend_score}
            </div>
            <div className="text-xs text-gray-500">趋势分</div>
          </div>
        </div>
      </div>
      
      {/* 核心数据 */}
      <div className="p-4 grid grid-cols-3 gap-3 bg-white/5">
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-sm font-medium text-white">
            <BarChart3 className="w-3 h-3 text-cyber-blue" />
            {product.sales_volume || '-'}
          </div>
          <div className="text-xs text-gray-500">销量</div>
        </div>
        <div className="text-center border-x border-white/10">
          <div className="flex items-center justify-center gap-1 text-sm font-medium text-white">
            <Euro className="w-3 h-3 text-energy-orange" />
            {product.price_range || '-'}
          </div>
          <div className="text-xs text-gray-500">价格</div>
        </div>
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-sm font-medium text-cyber-green">
            <TrendingUp className="w-3 h-3" />
            {product.growth_rate || '-'}
          </div>
          <div className="text-xs text-gray-500">增长</div>
        </div>
      </div>
      
      {/* AI分析摘要 */}
      {product.ai_analysis && (
        <div className="px-4 py-3 border-t border-white/5">
          <p className="text-sm text-gray-400 line-clamp-2">
            💡 {product.ai_analysis}
          </p>
        </div>
      )}
      
      {/* 展开详情 */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-4 py-3 border-t border-white/5 space-y-3"
          >
            {product.ai_opportunity && (
              <div className="bg-cyber-blue/10 rounded-lg p-3">
                <div className="flex items-center gap-1 text-xs text-cyber-blue mb-1">
                  <Sparkles className="w-3 h-3" />
                  商机分析
                </div>
                <p className="text-sm text-gray-300">{product.ai_opportunity}</p>
              </div>
            )}
            
            {product.ai_logistics_tips && (
              <div className="bg-cyber-green/10 rounded-lg p-3">
                <div className="flex items-center gap-1 text-xs text-cyber-green mb-1">
                  <Truck className="w-3 h-3" />
                  物流建议
                </div>
                <p className="text-sm text-gray-300">{product.ai_logistics_tips}</p>
              </div>
            )}
            
            {product.keywords && product.keywords.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {product.keywords.map((kw, i) => (
                  <span key={i} className="px-2 py-0.5 text-xs bg-white/10 text-gray-400 rounded">
                    {kw}
                  </span>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* 底部操作栏 */}
      <div className="px-4 py-3 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          {product.is_email_sent && (
            <span className="flex items-center gap-1 text-cyber-green">
              <Mail className="w-3 h-3" /> 已通知
            </span>
          )}
          {product.is_added_to_knowledge && (
            <span className="flex items-center gap-1 text-cyber-blue">
              <BookOpen className="w-3 h-3" /> 已存库
            </span>
          )}
          <span>
            {product.discovered_at ? new Date(product.discovered_at).toLocaleDateString('zh-CN') : '-'}
          </span>
        </div>
        
        <div className="flex items-center gap-3">
          {product.source_url && (
            <a
              href={product.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-cyber-blue hover:text-cyber-blue/80"
            >
              <ExternalLink className="w-3 h-3" />
              来源
            </a>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-3 h-3" />
                收起
              </>
            ) : (
              <>
                <ChevronDown className="w-3 h-3" />
                详情
              </>
            )}
          </button>
        </div>
      </div>
    </motion.div>
  )
}

export default function ProductTrendsPage() {
  const [products, setProducts] = useState<ProductTrend[]>([])
  const [stats, setStats] = useState<ProductStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [discovering, setDiscovering] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [category, setCategory] = useState<string>('')
  const [minScore, setMinScore] = useState<string>('')
  const [search, setSearch] = useState('')

  const loadProducts = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page: String(page),
        page_size: '12'
      })
      
      if (category) params.append('category', category)
      if (minScore) params.append('min_score', minScore)
      if (search) params.append('search', search)
      
      const res = await fetch(`${API_BASE}/api/products?${params}`)
      const data = await res.json()
      
      setProducts(data.items || [])
      setTotal(data.total || 0)
    } catch (error) {
      console.error('加载产品趋势失败:', error)
    } finally {
      setLoading(false)
    }
  }, [page, category, minScore, search])

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/products/stats`)
      const data = await res.json()
      setStats(data)
    } catch (error) {
      console.error('加载统计失败:', error)
    }
  }

  const handleDiscover = async () => {
    if (discovering) return
    
    try {
      setDiscovering(true)
      const res = await fetch(`${API_BASE}/api/products/discover`, {
        method: 'POST'
      })
      const data = await res.json()
      
      if (data.error) {
        alert(`发现失败: ${data.error}`)
      } else {
        alert(`✅ 发现完成！找到 ${data.total_products || 0} 个产品趋势`)
        loadProducts()
        loadStats()
      }
    } catch (error) {
      console.error('触发发现失败:', error)
      alert('触发发现失败，请检查后端服务')
    } finally {
      setDiscovering(false)
    }
  }

  useEffect(() => {
    loadProducts()
    loadStats()
  }, [loadProducts])

  const totalPages = Math.ceil(total / 12)

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShoppingCart className="w-7 h-7 text-neon-purple" />
            欧洲产品趋势
          </h1>
          <p className="text-gray-400 mt-1">
            小猎自动发现欧洲跨境电商热门产品，为物流业务提供市场洞察
          </p>
        </div>
        
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleDiscover}
          disabled={discovering}
          className={`btn-cyber flex items-center gap-2 ${
            discovering ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {discovering ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              发现中...
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              发现新趋势
            </>
          )}
        </motion.button>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-card p-4"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-neon-purple/20 flex items-center justify-center">
                <Package className="w-5 h-5 text-neon-purple" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{stats.total}</div>
                <div className="text-sm text-gray-400">总产品数</div>
              </div>
            </div>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card p-4"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-cyber-blue/20 flex items-center justify-center">
                <RefreshCw className="w-5 h-5 text-cyber-blue" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{stats.today}</div>
                <div className="text-sm text-gray-400">今日新发现</div>
              </div>
            </div>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass-card p-4"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-cyber-green/20 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-cyber-green" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{stats.high_trend}</div>
                <div className="text-sm text-gray-400">高趋势产品</div>
              </div>
            </div>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass-card p-4"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-energy-orange/20 flex items-center justify-center">
                <Mail className="w-5 h-5 text-energy-orange" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{stats.emailed}</div>
                <div className="text-sm text-gray-400">已发邮件通知</div>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* 过滤器 */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400">筛选:</span>
          </div>
          
          <select
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-cyber-blue/50"
          >
            <option value="">全部评分</option>
            <option value="70">≥70 高趋势</option>
            <option value="50">≥50 中趋势</option>
            <option value="30">≥30</option>
          </select>
          
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="输入类别"
            className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyber-blue/50 w-32"
          />
          
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索产品名称..."
                className="w-full pl-9 pr-4 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyber-blue/50"
              />
            </div>
          </div>
          
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => {
              setPage(1)
              loadProducts()
            }}
            className="px-4 py-1.5 bg-cyber-blue/20 text-cyber-blue rounded-lg text-sm hover:bg-cyber-blue/30 transition-colors"
          >
            筛选
          </motion.button>
        </div>
      </div>

      {/* 产品列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-cyber-blue animate-spin" />
        </div>
      ) : products.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Package className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <div className="text-gray-400 mb-4">暂无产品趋势数据</div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleDiscover}
            disabled={discovering}
            className="btn-cyber"
          >
            立即发现热门产品
          </motion.button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 glass-card text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:border-cyber-blue/30"
              >
                上一页
              </motion.button>
              
              <span className="px-4 py-2 text-gray-400">
                {page} / {totalPages}
              </span>
              
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 glass-card text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:border-cyber-blue/30"
              >
                下一页
              </motion.button>
            </div>
          )}
        </>
      )}

      {/* 最近发现 */}
      {stats && stats.recent_products && stats.recent_products.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6"
        >
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Globe className="w-5 h-5 text-cyber-blue" />
            最近发现
          </h3>
          <div className="space-y-3">
            {stats.recent_products.map((p, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium text-sm ${
                    p.score >= 70 ? 'bg-cyber-green/20 text-cyber-green' : 
                    p.score >= 50 ? 'bg-energy-orange/20 text-energy-orange' : 
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {p.score}
                  </div>
                  <div>
                    <div className="font-medium text-white">{p.name}</div>
                    <div className="text-xs text-gray-500">{p.category}</div>
                  </div>
                </div>
                <div className="text-xs text-gray-500">
                  {p.created_at ? new Date(p.created_at).toLocaleDateString('zh-CN') : '-'}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}
