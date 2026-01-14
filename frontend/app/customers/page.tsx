'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
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
  Users
} from 'lucide-react'
import Link from 'next/link'

interface Customer {
  id: string
  name: string
  company: string | null
  intentLevel: 'S' | 'A' | 'B' | 'C'
  intentScore: number
  phone: string | null
  source: string
  lastContact: string | null
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
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  
  // 从API获取真实数据
  useEffect(() => {
    const fetchCustomers = async () => {
      setLoading(true)
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
              source: c.source || '微信',
              lastContact: c.last_contact_at ? formatTime(c.last_contact_at) : null
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
    
    fetchCustomers()
    // 每30秒刷新
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
  
  // 筛选客户（本地搜索作为备用）
  const filteredCustomers = customers
  
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
        
        {loading ? (
          <div className="text-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-cyber-blue mx-auto mb-4" />
            <p className="text-gray-500">加载客户数据...</p>
          </div>
        ) : filteredCustomers.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-400 mb-2">暂无客户数据</p>
            <p className="text-gray-500 text-sm">当客户通过企业微信联系你时，客户记录会自动创建</p>
          </div>
        ) : null}
      </div>
    </div>
  )
}
