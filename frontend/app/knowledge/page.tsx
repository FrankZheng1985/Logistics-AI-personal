'use client'

import { useState } from 'react'
import { BookOpen, Search, Plus, Filter, ChevronRight, Star, Clock, Globe } from 'lucide-react'

interface KnowledgeItem {
  id: string
  category: string
  title: string
  summary: string
  experience_level: 'beginner' | 'intermediate' | 'expert'
  applicable_routes: string[]
  usage_count: number
  is_verified: boolean
}

const categories = [
  { id: 'all', name: '全部', count: 156 },
  { id: 'clearance', name: '清关政策', count: 42 },
  { id: 'transit', name: '时效航线', count: 35 },
  { id: 'pricing', name: '报价策略', count: 28 },
  { id: 'risk', name: '风险管理', count: 18 },
  { id: 'faq', name: '常见问题', count: 23 },
  { id: 'terminology', name: '行业术语', count: 10 }
]

const mockKnowledge: KnowledgeItem[] = [
  {
    id: '1',
    category: 'clearance',
    title: '美国清关门槛及注意事项',
    summary: '$800以下免税，需注意FDA/FCC认证要求，严查知识产权...',
    experience_level: 'intermediate',
    applicable_routes: ['中国→美国'],
    usage_count: 234,
    is_verified: true
  },
  {
    id: '2',
    category: 'transit',
    title: '中欧班列时效与优势',
    summary: '中欧班列运输时间约15-18天，比海运快一半，比空运便宜...',
    experience_level: 'beginner',
    applicable_routes: ['中国→欧洲'],
    usage_count: 189,
    is_verified: true
  },
  {
    id: '3',
    category: 'pricing',
    title: 'FBA头程报价策略',
    summary: '针对亚马逊卖家的FBA头程服务，需要考虑入仓费、标签费...',
    experience_level: 'expert',
    applicable_routes: ['中国→美国', '中国→欧洲'],
    usage_count: 156,
    is_verified: true
  },
  {
    id: '4',
    category: 'risk',
    title: '敏感品运输风险控制',
    summary: '带电产品、化妆品、液体等敏感品的运输注意事项和包装要求...',
    experience_level: 'expert',
    applicable_routes: [],
    usage_count: 98,
    is_verified: true
  },
  {
    id: '5',
    category: 'terminology',
    title: '常用物流术语对照表',
    summary: 'FCL整柜、LCL拼箱、DDU/DDP、CIF/FOB等术语详解...',
    experience_level: 'beginner',
    applicable_routes: [],
    usage_count: 312,
    is_verified: true
  }
]

const levelColors = {
  beginner: 'text-green-400 bg-green-400/10',
  intermediate: 'text-blue-400 bg-blue-400/10',
  expert: 'text-purple-400 bg-purple-400/10'
}

const levelNames = {
  beginner: '入门',
  intermediate: '熟练',
  expert: '专家'
}

export default function KnowledgePage() {
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [knowledge] = useState<KnowledgeItem[]>(mockKnowledge)

  const filteredKnowledge = knowledge.filter(item => {
    const matchCategory = selectedCategory === 'all' || item.category === selectedCategory
    const matchSearch = !searchQuery || 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.summary.toLowerCase().includes(searchQuery.toLowerCase())
    return matchCategory && matchSearch
  })

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <BookOpen className="w-7 h-7 text-cyber-blue" />
            知识库管理
          </h1>
          <p className="text-gray-400 mt-1">物流专业知识库，让AI员工达到行业老手水准</p>
        </div>
        <button className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity">
          <Plus className="w-4 h-4" />
          添加知识
        </button>
      </div>

      {/* 搜索和筛选 */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="搜索知识..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-dark-card border border-gray-700 rounded-xl text-white focus:border-cyber-blue focus:outline-none"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-3 bg-dark-card border border-gray-700 rounded-xl text-gray-400 hover:text-white transition-colors">
          <Filter className="w-5 h-5" />
          筛选
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 分类侧边栏 */}
        <div className="lg:col-span-1">
          <div className="bg-dark-card rounded-xl p-4">
            <h3 className="text-sm font-medium text-gray-400 mb-4">知识分类</h3>
            <div className="space-y-1">
              {categories.map(cat => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg transition-colors ${
                    selectedCategory === cat.id
                      ? 'bg-cyber-blue text-white'
                      : 'text-gray-400 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  <span>{cat.name}</span>
                  <span className="text-sm opacity-70">{cat.count}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 知识列表 */}
        <div className="lg:col-span-3 space-y-4">
          {filteredKnowledge.length === 0 ? (
            <div className="bg-dark-card rounded-xl p-12 text-center">
              <BookOpen className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 text-lg">暂无相关知识</p>
            </div>
          ) : (
            filteredKnowledge.map(item => (
              <div
                key={item.id}
                className="bg-dark-card rounded-xl p-5 hover:ring-1 hover:ring-cyber-blue/50 transition-all cursor-pointer group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-white font-medium group-hover:text-cyber-blue transition-colors">
                        {item.title}
                      </h3>
                      {item.is_verified && (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-green-400/10 text-green-400 text-xs rounded-full">
                          <Star className="w-3 h-3" />
                          已验证
                        </span>
                      )}
                      <span className={`px-2 py-0.5 text-xs rounded-full ${levelColors[item.experience_level]}`}>
                        {levelNames[item.experience_level]}
                      </span>
                    </div>
                    <p className="text-gray-400 text-sm mb-3">{item.summary}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      {item.applicable_routes.length > 0 && (
                        <span className="flex items-center gap-1">
                          <Globe className="w-3 h-3" />
                          {item.applicable_routes.join(', ')}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        使用 {item.usage_count} 次
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-cyber-blue transition-colors" />
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
