'use client'

import { useState, useEffect, useCallback } from 'react'

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

function ProductCard({ product }: { product: ProductTrend }) {
  const [expanded, setExpanded] = useState(false)
  
  const getScoreColor = (score: number) => {
    if (score >= 70) return 'bg-green-500'
    if (score >= 50) return 'bg-yellow-500'
    return 'bg-gray-400'
  }
  
  const getPlatformEmoji = (platform: string | null) => {
    const map: Record<string, string> = {
      'amazon': '🛒',
      'temu': '🛍️',
      'shein': '👗',
      'google': '🔍',
      'baidu': '🔎'
    }
    return platform ? (map[platform] || '📦') : '📦'
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      {/* 头部 */}
      <div className="p-4 border-b border-gray-50">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">{getPlatformEmoji(product.source_platform)}</span>
              <h3 className="font-semibold text-gray-800 line-clamp-1">
                {product.product_name}
              </h3>
            </div>
            {product.category && (
              <span className="inline-block px-2 py-0.5 text-xs bg-purple-50 text-purple-600 rounded">
                {product.category}
              </span>
            )}
          </div>
          
          {/* 趋势评分 */}
          <div className="flex flex-col items-center">
            <div className={`w-12 h-12 rounded-full ${getScoreColor(product.trend_score)} flex items-center justify-center text-white font-bold`}>
              {product.trend_score}
            </div>
            <span className="text-xs text-gray-400 mt-1">趋势分</span>
          </div>
        </div>
      </div>
      
      {/* 核心数据 */}
      <div className="p-4 grid grid-cols-3 gap-3 bg-gray-50/50">
        <div className="text-center">
          <div className="text-sm font-medium text-gray-800">
            {product.sales_volume || '-'}
          </div>
          <div className="text-xs text-gray-400">销量</div>
        </div>
        <div className="text-center border-x border-gray-100">
          <div className="text-sm font-medium text-gray-800">
            {product.price_range || '-'}
          </div>
          <div className="text-xs text-gray-400">价格</div>
        </div>
        <div className="text-center">
          <div className="text-sm font-medium text-green-600">
            {product.growth_rate || '-'}
          </div>
          <div className="text-xs text-gray-400">增长</div>
        </div>
      </div>
      
      {/* AI分析摘要 */}
      {product.ai_analysis && (
        <div className="px-4 py-3 border-t border-gray-50">
          <div className="text-sm text-gray-600 line-clamp-2">
            {product.ai_analysis}
          </div>
        </div>
      )}
      
      {/* 展开详情 */}
      {expanded && (
        <div className="px-4 py-3 border-t border-gray-100 bg-blue-50/30 space-y-3">
          {product.ai_opportunity && (
            <div>
              <div className="text-xs font-medium text-blue-600 mb-1">💡 商机分析</div>
              <div className="text-sm text-gray-700">{product.ai_opportunity}</div>
            </div>
          )}
          
          {product.ai_logistics_tips && (
            <div>
              <div className="text-xs font-medium text-green-600 mb-1">🚚 物流建议</div>
              <div className="text-sm text-gray-700">{product.ai_logistics_tips}</div>
            </div>
          )}
          
          {product.keywords && product.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {product.keywords.map((kw, i) => (
                <span key={i} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded">
                  {kw}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* 底部操作栏 */}
      <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          {product.is_email_sent && (
            <span className="flex items-center gap-1 text-green-500">
              ✉️ 已发送邮件
            </span>
          )}
          {product.is_added_to_knowledge && (
            <span className="flex items-center gap-1 text-blue-500">
              📚 已存知识库
            </span>
          )}
          <span>
            {product.discovered_at ? new Date(product.discovered_at).toLocaleDateString('zh-CN') : '-'}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {product.source_url && (
            <a
              href={product.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-500 hover:text-blue-600"
            >
              查看来源 →
            </a>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {expanded ? '收起' : '展开详情'}
          </button>
        </div>
      </div>
    </div>
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
  const [minScore, setMinScore] = useState<number | undefined>()
  const [search, setSearch] = useState('')

  const loadProducts = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page: String(page),
        page_size: '12'
      })
      
      if (category) params.append('category', category)
      if (minScore) params.append('min_score', String(minScore))
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
        alert(`发现完成！找到 ${data.total_products || 0} 个产品趋势`)
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
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
              🛒 欧洲产品趋势
            </h1>
            <p className="text-gray-500 mt-1">
              小猎自动发现欧洲跨境电商热门产品，为物流业务提供市场洞察
            </p>
          </div>
          
          <button
            onClick={handleDiscover}
            disabled={discovering}
            className={`px-6 py-3 rounded-lg font-medium transition-all flex items-center gap-2 ${
              discovering 
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:shadow-lg'
            }`}
          >
            {discovering ? (
              <>
                <span className="animate-spin">⏳</span>
                发现中...
              </>
            ) : (
              <>
                🔍 发现新趋势
              </>
            )}
          </button>
        </div>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-3xl font-bold text-gray-800">{stats.total}</div>
            <div className="text-sm text-gray-500">总产品数</div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-3xl font-bold text-blue-500">{stats.today}</div>
            <div className="text-sm text-gray-500">今日新发现</div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-3xl font-bold text-green-500">{stats.high_trend}</div>
            <div className="text-sm text-gray-500">高趋势产品</div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-3xl font-bold text-purple-500">{stats.emailed}</div>
            <div className="text-sm text-gray-500">已发邮件通知</div>
          </div>
        </div>
      )}

      {/* 过滤器 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 mb-6">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">最低评分:</span>
            <select
              value={minScore || ''}
              onChange={(e) => setMinScore(e.target.value ? Number(e.target.value) : undefined)}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">全部</option>
              <option value="70">≥70 (高趋势)</option>
              <option value="50">≥50 (中趋势)</option>
              <option value="30">≥30</option>
            </select>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">类别:</span>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="输入类别"
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 w-32"
            />
          </div>
          
          <div className="flex-1">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索产品名称..."
              className="w-full px-4 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          
          <button
            onClick={() => {
              setPage(1)
              loadProducts()
            }}
            className="px-4 py-1.5 bg-purple-500 text-white rounded-lg text-sm hover:bg-purple-600 transition-colors"
          >
            筛选
          </button>
        </div>
      </div>

      {/* 产品列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin text-4xl">🔄</div>
        </div>
      ) : products.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">📦</div>
          <div className="text-gray-500 mb-4">暂无产品趋势数据</div>
          <button
            onClick={handleDiscover}
            disabled={discovering}
            className="px-6 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
          >
            立即发现热门产品
          </button>
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
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 rounded-lg border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                上一页
              </button>
              
              <span className="px-4 py-2 text-gray-600">
                {page} / {totalPages}
              </span>
              
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 rounded-lg border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}

      {/* 最近发现 */}
      {stats && stats.recent_products && stats.recent_products.length > 0 && (
        <div className="mt-8 bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">🕐 最近发现</h3>
          <div className="space-y-3">
            {stats.recent_products.map((p, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center font-medium">
                    {p.score}
                  </span>
                  <div>
                    <div className="font-medium text-gray-800">{p.name}</div>
                    <div className="text-xs text-gray-400">{p.category}</div>
                  </div>
                </div>
                <div className="text-xs text-gray-400">
                  {p.created_at ? new Date(p.created_at).toLocaleDateString('zh-CN') : '-'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
