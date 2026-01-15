'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Search, Plus, Filter, ChevronRight, Star, Clock, Globe, X, Loader2, Trash2, Edit2 } from 'lucide-react'

interface KnowledgeItem {
  id: string
  content: string
  knowledge_type: string
  type_name: string
  source: string
  tags: string[]
  is_verified: boolean
  usage_count: number
  created_at: string
}

interface KnowledgeType {
  type: string
  name: string
  description: string
}

// 新建/编辑知识弹窗
function KnowledgeModal({
  knowledge,
  types,
  onClose,
  onSave
}: {
  knowledge: KnowledgeItem | null
  types: KnowledgeType[]
  onClose: () => void
  onSave: (data: any) => Promise<void>
}) {
  const [content, setContent] = useState(knowledge?.content || '')
  const [knowledgeType, setKnowledgeType] = useState(knowledge?.knowledge_type || 'faq')
  const [tags, setTags] = useState<string[]>(knowledge?.tags || [])
  const [tagInput, setTagInput] = useState('')
  const [isVerified, setIsVerified] = useState(knowledge?.is_verified || false)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!content.trim()) {
      alert('请输入知识内容')
      return
    }
    setSaving(true)
    try {
      await onSave({
        id: knowledge?.id,
        content,
        knowledge_type: knowledgeType,
        tags,
        is_verified: isVerified
      })
      onClose()
    } catch (error) {
      alert('保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  const addTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()])
      setTagInput('')
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
        className="bg-dark-purple/90 backdrop-blur-xl border border-white/10 rounded-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <h2 className="text-xl font-bold text-white">
            {knowledge ? '编辑知识' : '添加知识'}
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-6 space-y-6">
          {/* 知识类型 */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">知识类型</label>
            <select
              value={knowledgeType}
              onChange={e => setKnowledgeType(e.target.value)}
              className="w-full px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
            >
              {types.map(t => (
                <option key={t.type} value={t.type}>{t.name}</option>
              ))}
            </select>
          </div>

          {/* 知识内容 */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">知识内容</label>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              rows={6}
              className="w-full px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none resize-none"
              placeholder="输入知识内容，AI员工会在对话中使用这些知识..."
            />
          </div>

          {/* 标签 */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">标签</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {tags.map((tag, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-cyber-blue/20 text-cyber-blue rounded-full text-sm flex items-center gap-2"
                >
                  {tag}
                  <button onClick={() => setTags(tags.filter((_, i) => i !== index))} className="hover:text-white">
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addTag()}
                className="flex-1 px-4 py-2 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="输入标签后按回车"
              />
              <button onClick={addTag} className="px-4 py-2 bg-cyber-blue/20 text-cyber-blue rounded-lg hover:bg-cyber-blue/30">
                添加
              </button>
            </div>
          </div>

          {/* 是否验证 */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={isVerified}
              onChange={e => setIsVerified(e.target.checked)}
              className="w-5 h-5 rounded bg-deep-space/50 border-gray-700 text-cyber-blue focus:ring-cyber-blue"
            />
            <span className="text-white">标记为已验证</span>
            <span className="text-gray-500 text-sm">已验证的知识会优先被AI使用</span>
          </label>
        </div>

        {/* 底部按钮 */}
        <div className="flex justify-end gap-3 p-6 border-t border-white/10">
          <button
            onClick={onClose}
            className="px-6 py-2.5 text-gray-400 hover:text-white transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// 知识详情弹窗
function KnowledgeDetailModal({
  knowledge,
  onClose,
  onEdit,
  onDelete
}: {
  knowledge: KnowledgeItem
  onClose: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    if (!confirm('确定要删除这条知识吗？')) return
    setDeleting(true)
    await onDelete()
    setDeleting(false)
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
        className="bg-dark-purple/90 backdrop-blur-xl border border-white/10 rounded-xl w-full max-w-2xl mx-4"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white">{knowledge.type_name}</h2>
            {knowledge.is_verified && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-green-400/10 text-green-400 text-xs rounded-full">
                <Star className="w-3 h-3" />
                已验证
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6">
          <p className="text-gray-200 whitespace-pre-wrap mb-6">{knowledge.content}</p>
          
          {knowledge.tags && knowledge.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {knowledge.tags.map((tag, index) => (
                <span key={index} className="px-2 py-1 bg-cyber-blue/20 text-cyber-blue text-xs rounded">
                  {tag}
                </span>
              ))}
            </div>
          )}

          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              使用 {knowledge.usage_count} 次
            </span>
            <span>来源: {knowledge.source}</span>
            <span>创建: {new Date(knowledge.created_at).toLocaleDateString('zh-CN')}</span>
          </div>
        </div>

        <div className="flex justify-between p-6 border-t border-white/10">
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="flex items-center gap-2 px-4 py-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
          >
            {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            删除
          </button>
          <button
            onClick={onEdit}
            className="flex items-center gap-2 px-4 py-2 text-cyber-blue hover:bg-cyber-blue/10 rounded-lg transition-colors"
          >
            <Edit2 className="w-4 h-4" />
            编辑
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default function KnowledgePage() {
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([])
  const [types, setTypes] = useState<KnowledgeType[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedKnowledge, setSelectedKnowledge] = useState<KnowledgeItem | null>(null)
  const [editingKnowledge, setEditingKnowledge] = useState<KnowledgeItem | null>(null)
  const [stats, setStats] = useState<Record<string, number>>({})

  // 获取知识类型
  const fetchTypes = async () => {
    try {
      const res = await fetch('/api/knowledge/types')
      if (res.ok) {
        const data = await res.json()
        setTypes(data.types || [])
      }
    } catch (error) {
      console.error('获取知识类型失败:', error)
    }
  }

  // 获取知识列表
  const fetchKnowledge = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (selectedCategory !== 'all') {
        params.append('knowledge_type', selectedCategory)
      }
      if (searchQuery) {
        params.append('query', searchQuery)
      }
      
      const res = await fetch(`/api/knowledge/?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setKnowledge(data.items || [])
        
        // 计算各类型数量
        const newStats: Record<string, number> = { all: data.items?.length || 0 }
        data.items?.forEach((item: KnowledgeItem) => {
          newStats[item.knowledge_type] = (newStats[item.knowledge_type] || 0) + 1
        })
        setStats(newStats)
      }
    } catch (error) {
      console.error('获取知识列表失败:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedCategory, searchQuery])

  // 保存知识
  const handleSaveKnowledge = async (data: any) => {
    const url = data.id ? `/api/knowledge/${data.id}` : '/api/knowledge/'
    const method = data.id ? 'PUT' : 'POST'
    
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: data.content,
        knowledge_type: data.knowledge_type,
        tags: data.tags,
        is_verified: data.is_verified
      })
    })
    
    if (!res.ok) throw new Error('保存失败')
    await fetchKnowledge()
  }

  // 删除知识
  const handleDeleteKnowledge = async (id: string) => {
    const res = await fetch(`/api/knowledge/${id}`, { method: 'DELETE' })
    if (res.ok) {
      setSelectedKnowledge(null)
      await fetchKnowledge()
    }
  }

  useEffect(() => {
    fetchTypes()
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchKnowledge()
  }, [fetchKnowledge])

  // 构建分类列表
  const categories = [
    { id: 'all', name: '全部', count: stats.all || 0 },
    ...types.map(t => ({
      id: t.type,
      name: t.name,
      count: stats[t.type] || 0
    }))
  ]

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
        <button 
          onClick={() => {
            setEditingKnowledge(null)
            setShowAddModal(true)
          }}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity"
        >
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
            className="w-full pl-12 pr-4 py-3 bg-dark-purple/40 border border-gray-700 rounded-xl text-white focus:border-cyber-blue focus:outline-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 分类侧边栏 */}
        <div className="lg:col-span-1">
          <div className="bg-dark-purple/40 rounded-xl p-4">
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
          {loading ? (
            <div className="bg-dark-purple/40 rounded-xl p-12 text-center">
              <Loader2 className="w-8 h-8 text-cyber-blue mx-auto mb-4 animate-spin" />
              <p className="text-gray-400">加载中...</p>
            </div>
          ) : knowledge.length === 0 ? (
            <div className="bg-dark-purple/40 rounded-xl p-12 text-center">
              <BookOpen className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 text-lg mb-4">暂无相关知识</p>
              <button
                onClick={() => setShowAddModal(true)}
                className="text-cyber-blue hover:underline"
              >
                点击添加第一条知识
              </button>
            </div>
          ) : (
            knowledge.map(item => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={() => setSelectedKnowledge(item)}
                className="bg-dark-purple/40 rounded-xl p-5 hover:ring-1 hover:ring-cyber-blue/50 transition-all cursor-pointer group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="px-2 py-0.5 bg-cyber-blue/20 text-cyber-blue text-xs rounded-full">
                        {item.type_name}
                      </span>
                      {item.is_verified && (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-green-400/10 text-green-400 text-xs rounded-full">
                          <Star className="w-3 h-3" />
                          已验证
                        </span>
                      )}
                    </div>
                    <p className="text-gray-300 text-sm mb-3 line-clamp-2">{item.content}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      {item.tags && item.tags.length > 0 && (
                        <span className="flex items-center gap-1">
                          {item.tags.slice(0, 3).join(', ')}
                          {item.tags.length > 3 && '...'}
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
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* 添加/编辑弹窗 */}
      <AnimatePresence>
        {showAddModal && (
          <KnowledgeModal
            knowledge={editingKnowledge}
            types={types}
            onClose={() => {
              setShowAddModal(false)
              setEditingKnowledge(null)
            }}
            onSave={handleSaveKnowledge}
          />
        )}
      </AnimatePresence>

      {/* 详情弹窗 */}
      <AnimatePresence>
        {selectedKnowledge && !showAddModal && (
          <KnowledgeDetailModal
            knowledge={selectedKnowledge}
            onClose={() => setSelectedKnowledge(null)}
            onEdit={() => {
              setEditingKnowledge(selectedKnowledge)
              setSelectedKnowledge(null)
              setShowAddModal(true)
            }}
            onDelete={() => handleDeleteKnowledge(selectedKnowledge.id)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
