'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  Search, 
  Filter, 
  ChevronDown,
  Phone,
  MessageSquare,
  TrendingUp,
  MoreVertical,
  ArrowLeft
} from 'lucide-react'
import Link from 'next/link'

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

// 客户行组件
function CustomerRow({ 
  customer,
  onSelect
}: { 
  customer: any
  onSelect: () => void 
}) {
  const isHighIntent = customer.intentLevel === 'S' || customer.intentLevel === 'A'
  
  return (
    <motion.tr 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors ${
        isHighIntent ? 'bg-cyber-green/5' : ''
      }`}
      onClick={onSelect}
    >
      <td className="p-4">
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
      <td className="p-4">
        <IntentBadge level={customer.intentLevel} />
      </td>
      <td className="p-4">
        <span className="font-number text-cyber-blue">{customer.intentScore}</span>
      </td>
      <td className="p-4 text-gray-400">
        {customer.phone || '-'}
      </td>
      <td className="p-4 text-gray-400">
        {customer.source}
      </td>
      <td className="p-4 text-gray-500 text-sm">
        {customer.lastContact || '从未联系'}
      </td>
      <td className="p-4">
        <div className="flex items-center gap-2">
          <button className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <Phone className="w-4 h-4 text-gray-400" />
          </button>
          <button className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <MessageSquare className="w-4 h-4 text-gray-400" />
          </button>
          <button className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <MoreVertical className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </td>
    </motion.tr>
  )
}

export default function CustomersPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterLevel, setFilterLevel] = useState<string | null>(null)
  
  // 模拟数据
  const [customers] = useState([
    { id: '1', name: '张先生', company: '广州某贸易公司', intentLevel: 'S' as const, intentScore: 85, phone: '138****1234', source: '微信', lastContact: '10分钟前' },
    { id: '2', name: '李经理', company: '深圳电子科技', intentLevel: 'A' as const, intentScore: 72, phone: '139****5678', source: '网站', lastContact: '1小时前' },
    { id: '3', name: '王总', company: '东莞制造厂', intentLevel: 'A' as const, intentScore: 65, phone: '136****9012', source: '广告', lastContact: '3小时前' },
    { id: '4', name: '陈小姐', company: '佛山外贸公司', intentLevel: 'B' as const, intentScore: 45, phone: '137****3456', source: '微信', lastContact: '昨天' },
    { id: '5', name: '刘先生', company: '惠州电商', intentLevel: 'B' as const, intentScore: 38, phone: '135****7890', source: '转介绍', lastContact: '2天前' },
    { id: '6', name: '赵经理', company: '中山家具厂', intentLevel: 'C' as const, intentScore: 22, phone: '133****1122', source: '网站', lastContact: '1周前' },
  ])
  
  // 筛选客户
  const filteredCustomers = customers.filter(c => {
    if (filterLevel && c.intentLevel !== filterLevel) return false
    if (searchQuery && !c.name.includes(searchQuery) && !c.company?.includes(searchQuery)) return false
    return true
  })
  
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
            <p className="text-gray-400 text-sm">共 {customers.length} 位客户</p>
          </div>
        </div>
        <button className="btn-cyber flex items-center gap-2">
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
        <div className="relative">
          <button className="flex items-center gap-2 px-4 py-3 glass-card hover:border-cyber-blue/50 transition-colors">
            <Filter className="w-4 h-4" />
            意向等级
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>
        <div className="flex gap-2">
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
            {filteredCustomers.map((customer) => (
              <CustomerRow 
                key={customer.id} 
                customer={customer}
                onSelect={() => console.log('Select:', customer.id)}
              />
            ))}
          </tbody>
        </table>
        
        {filteredCustomers.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            没有找到匹配的客户
          </div>
        )}
      </div>
    </div>
  )
}
