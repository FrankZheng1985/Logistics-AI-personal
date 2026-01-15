'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mail, Plus, Play, Pause, Edit2, Trash2, Users, Clock, TrendingUp, Loader2, RefreshCw, AlertCircle, X } from 'lucide-react'

interface MarketingSequence {
  id: string
  name: string
  description: string
  trigger_type: string
  status: 'active' | 'paused' | 'draft'
  email_count: number
  enrolled_count: number
  converted_count: number
  conversion_rate: number
  created_at: string
}

interface Stats {
  total: number
  active: number
  total_enrolled: number
  avg_conversion_rate: number
}

// 触发类型名称映射
const triggerNames: Record<string, string> = {
  'first_inquiry': '首次询价',
  'no_reply_3d': '报价后3天未回复',
  'inactive_30d': '30天未联系',
  'manual': '手动触发'
}

const statusColors = {
  active: 'text-green-400 bg-green-400/10',
  paused: 'text-yellow-400 bg-yellow-400/10',
  draft: 'text-gray-400 bg-gray-400/10'
}

const statusNames = {
  active: '运行中',
  paused: '已暂停',
  draft: '草稿'
}

// 创建序列弹窗
function CreateSequenceModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [triggerType, setTriggerType] = useState('first_inquiry')
  const [creating, setCreating] = useState(false)

  const handleCreate = async () => {
    if (!name.trim()) {
      alert('请输入序列名称')
      return
    }

    setCreating(true)
    try {
      const res = await fetch('/api/marketing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description,
          trigger_condition: triggerType
        })
      })

      if (res.ok) {
        alert('创建成功！')
        onCreated()
        onClose()
      } else {
        const error = await res.json()
        alert(error.detail || '创建失败，请重试')
      }
    } catch (error) {
      console.error('创建失败:', error)
      alert('创建失败，请检查网络')
    } finally {
      setCreating(false)
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
        className="bg-dark-purple/90 backdrop-blur-xl border border-white/10 rounded-xl w-full max-w-md mx-4"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <h2 className="text-xl font-bold text-white">创建营销序列</h2>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">序列名称</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              placeholder="例如：新客户欢迎序列"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">序列描述</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              className="w-full px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none resize-none"
              placeholder="描述这个营销序列的目的和内容"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">触发条件</label>
            <select
              value={triggerType}
              onChange={e => setTriggerType(e.target.value)}
              className="w-full px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
            >
              <option value="first_inquiry">首次询价</option>
              <option value="no_reply_3d">报价后3天未回复</option>
              <option value="inactive_30d">30天未联系</option>
              <option value="manual">手动触发</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-3 p-6 border-t border-white/10">
          <button
            onClick={onClose}
            className="px-6 py-2.5 text-gray-400 hover:text-white transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {creating && <Loader2 className="w-4 h-4 animate-spin" />}
            {creating ? '创建中...' : '创建'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default function MarketingPage() {
  const [sequences, setSequences] = useState<MarketingSequence[]>([])
  const [stats, setStats] = useState<Stats>({
    total: 0,
    active: 0,
    total_enrolled: 0,
    avg_conversion_rate: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

  // 从API获取真实数据
  const fetchSequences = async () => {
    try {
      setError(null)
      const res = await fetch('/api/marketing')
      if (res.ok) {
        const data = await res.json()
        setSequences(data.items || [])
        setStats(data.stats || {
          total: 0,
          active: 0,
          total_enrolled: 0,
          avg_conversion_rate: 0
        })
      } else {
        setError('获取数据失败')
      }
    } catch (err) {
      console.error('获取营销序列失败:', err)
      setError('网络错误，请重试')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setLoading(true)
    fetchSequences()
    // 每30秒自动刷新
    const interval = setInterval(fetchSequences, 30000)
    return () => clearInterval(interval)
  }, [])

  // 切换序列状态
  const handleToggleStatus = async (sequenceId: string) => {
    try {
      const res = await fetch(`/api/marketing/${sequenceId}/toggle`, {
        method: 'POST'
      })
      if (res.ok) {
        await fetchSequences()
      } else {
        alert('操作失败，请重试')
      }
    } catch (err) {
      console.error('切换状态失败:', err)
      alert('操作失败，请重试')
    }
  }

  // 删除序列
  const handleDelete = async (sequenceId: string) => {
    if (!confirm('确定要删除这个营销序列吗？')) return
    
    try {
      const res = await fetch(`/api/marketing/${sequenceId}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        await fetchSequences()
      } else {
        alert('删除失败，请重试')
      }
    } catch (err) {
      console.error('删除失败:', err)
      alert('删除失败，请重试')
    }
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Mail className="w-7 h-7 text-cyber-blue" />
            营销序列
          </h1>
          <p className="text-gray-400 mt-1">自动化邮件营销序列，提升客户转化率</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => {
              setLoading(true)
              fetchSequences()
            }}
            className="p-2 glass-card hover:border-cyber-blue/50 transition-colors"
            disabled={loading}
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button 
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" />
            创建序列
          </button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-400/10 rounded-lg">
              <Mail className="w-5 h-5 text-blue-400" />
            </div>
            <span className="text-gray-400">总序列数</span>
          </div>
          {loading ? (
            <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
          ) : (
            <p className="text-2xl font-bold text-white">{stats.total}</p>
          )}
        </div>
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-green-400/10 rounded-lg">
              <Play className="w-5 h-5 text-green-400" />
            </div>
            <span className="text-gray-400">运行中</span>
          </div>
          {loading ? (
            <Loader2 className="w-8 h-8 animate-spin text-green-400" />
          ) : (
            <p className="text-2xl font-bold text-white">{stats.active}</p>
          )}
        </div>
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-purple-400/10 rounded-lg">
              <Users className="w-5 h-5 text-purple-400" />
            </div>
            <span className="text-gray-400">总触达人数</span>
          </div>
          {loading ? (
            <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          ) : (
            <p className="text-2xl font-bold text-white">{stats.total_enrolled}</p>
          )}
        </div>
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-cyan-400/10 rounded-lg">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
            </div>
            <span className="text-gray-400">平均转化率</span>
          </div>
          {loading ? (
            <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
          ) : (
            <p className="text-2xl font-bold text-white">{stats.avg_conversion_rate}%</p>
          )}
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-alert-red/10 border border-alert-red/30 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-alert-red" />
          <span className="text-alert-red">{error}</span>
          <button 
            onClick={() => {
              setLoading(true)
              fetchSequences()
            }}
            className="ml-auto px-3 py-1 bg-alert-red/20 hover:bg-alert-red/30 rounded text-alert-red text-sm"
          >
            重试
          </button>
        </div>
      )}

      {/* 序列列表 */}
      {loading ? (
        <div className="text-center py-12">
          <Loader2 className="w-10 h-10 animate-spin text-cyber-blue mx-auto mb-4" />
          <p className="text-gray-400">加载营销序列数据...</p>
        </div>
      ) : sequences.length === 0 ? (
        <div className="bg-dark-purple/40 rounded-xl p-12 text-center">
          <Mail className="w-16 h-16 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-400 text-lg mb-2">暂无营销序列</p>
          <p className="text-gray-500 text-sm mb-6">创建您的第一个自动化邮件营销序列</p>
          <button 
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" />
            创建第一个序列
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {sequences.map(sequence => (
            <div
              key={sequence.id}
              className="bg-dark-purple/40 rounded-xl p-5 hover:ring-1 hover:ring-cyber-blue/50 transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-white font-semibold text-lg">{sequence.name}</h3>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${statusColors[sequence.status]}`}>
                      {statusNames[sequence.status]}
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm mb-4">{sequence.description || '暂无描述'}</p>
                  
                  <div className="flex items-center gap-6 text-sm">
                    <div className="flex items-center gap-2 text-gray-500">
                      <Clock className="w-4 h-4" />
                      <span>触发条件: {triggerNames[sequence.trigger_type] || sequence.trigger_type}</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-500">
                      <Mail className="w-4 h-4" />
                      <span>{sequence.email_count} 封邮件</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-500">
                      <Users className="w-4 h-4" />
                      <span>已触达 {sequence.enrolled_count} 人</span>
                    </div>
                    {sequence.conversion_rate > 0 && (
                      <div className="flex items-center gap-2 text-green-400">
                        <TrendingUp className="w-4 h-4" />
                        <span>转化率 {sequence.conversion_rate}%</span>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  {sequence.status === 'active' ? (
                    <button 
                      onClick={() => handleToggleStatus(sequence.id)}
                      className="p-2 text-yellow-400 hover:bg-yellow-400/10 rounded-lg transition-colors" 
                      title="暂停"
                    >
                      <Pause className="w-5 h-5" />
                    </button>
                  ) : sequence.status === 'paused' || sequence.status === 'draft' ? (
                    <button 
                      onClick={() => handleToggleStatus(sequence.id)}
                      className="p-2 text-green-400 hover:bg-green-400/10 rounded-lg transition-colors" 
                      title="启动"
                    >
                      <Play className="w-5 h-5" />
                    </button>
                  ) : null}
                  <button className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors" title="编辑">
                    <Edit2 className="w-5 h-5" />
                  </button>
                  <button 
                    onClick={() => handleDelete(sequence.id)}
                    className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors" 
                    title="删除"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 创建弹窗 */}
      <AnimatePresence>
        {showCreateModal && (
          <CreateSequenceModal
            onClose={() => setShowCreateModal(false)}
            onCreated={fetchSequences}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
