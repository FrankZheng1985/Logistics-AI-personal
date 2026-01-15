'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ClipboardCheck, Bot, Zap, Award, ChevronDown, ChevronUp, Edit2, X, Loader2, Save } from 'lucide-react'

interface AgentStandard {
  id: string
  agent_type: string
  standard_category: string
  standard_name: string
  standard_content: Record<string, any>
  quality_metrics: Record<string, any>
  version: number
  is_active: boolean
}

// AI员工名称映射
const agentNames: Record<string, string> = {
  'coordinator': '小调',
  'sales': '小销',
  'analyst': '小析',
  'copywriter': '小文',
  'video_creator': '小视',
  'follow_up': '小跟',
  'lead_hunter': '小猎',
}

// 编辑标准弹窗
function EditStandardModal({
  standard,
  onClose,
  onSave
}: {
  standard: AgentStandard
  onClose: () => void
  onSave: (id: string, data: any) => Promise<void>
}) {
  const [content, setContent] = useState(JSON.stringify(standard.standard_content, null, 2))
  const [metrics, setMetrics] = useState(JSON.stringify(standard.quality_metrics, null, 2))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    try {
      const parsedContent = JSON.parse(content)
      const parsedMetrics = JSON.parse(metrics)
      
      setSaving(true)
      setError('')
      
      await onSave(standard.id, {
        standard_content: parsedContent,
        quality_metrics: parsedMetrics
      })
      
      onClose()
    } catch (e) {
      setError('JSON格式错误，请检查输入')
    } finally {
      setSaving(false)
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
        className="bg-dark-purple/90 backdrop-blur-xl border border-white/10 rounded-xl w-full max-w-4xl mx-4 max-h-[80vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div>
            <h2 className="text-xl font-bold text-white">编辑工作标准</h2>
            <p className="text-gray-400 text-sm mt-1">
              {agentNames[standard.agent_type] || standard.agent_type} - {standard.standard_name} (v{standard.version})
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {error && (
            <div className="p-4 bg-red-400/10 border border-red-400/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Award className="w-4 h-4 inline mr-2" />
              标准内容 (JSON)
            </label>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              rows={10}
              className="w-full px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white font-mono text-sm focus:border-cyber-blue focus:outline-none resize-none"
              placeholder='{"key": "value"}'
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Zap className="w-4 h-4 inline mr-2" />
              质量指标 (JSON)
            </label>
            <textarea
              value={metrics}
              onChange={e => setMetrics(e.target.value)}
              rows={6}
              className="w-full px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white font-mono text-sm focus:border-cyber-blue focus:outline-none resize-none"
              placeholder='{"metric": "value"}'
            />
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
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default function StandardsPage() {
  const [standards, setStandards] = useState<AgentStandard[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)
  const [editingStandard, setEditingStandard] = useState<AgentStandard | null>(null)

  // 获取工作标准
  const fetchStandards = async () => {
    try {
      const res = await fetch('/api/standards')
      if (res.ok) {
        const data = await res.json()
        setStandards(data)
        // 默认展开第一个
        if (data.length > 0 && !expandedAgent) {
          setExpandedAgent(data[0].agent_type)
        }
      }
    } catch (error) {
      console.error('获取工作标准失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 更新工作标准
  const handleUpdateStandard = async (id: string, data: any) => {
    const res = await fetch(`/api/standards/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    
    if (!res.ok) throw new Error('更新失败')
    await fetchStandards()
  }

  useEffect(() => {
    fetchStandards()
  }, [])

  const toggleExpand = (agentType: string) => {
    setExpandedAgent(prev => prev === agentType ? null : agentType)
  }

  const renderValue = (value: any): string => {
    if (Array.isArray(value)) {
      return value.join('、')
    }
    if (typeof value === 'object' && value !== null) {
      return Object.entries(value).map(([k, v]) => `${k}: ${v}`).join(', ')
    }
    return String(value)
  }

  // 按员工类型分组
  const groupedStandards = standards.reduce((acc, s) => {
    if (!acc[s.agent_type]) {
      acc[s.agent_type] = []
    }
    acc[s.agent_type].push(s)
    return acc
  }, {} as Record<string, AgentStandard[]>)

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-cyber-blue" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <ClipboardCheck className="w-7 h-7 text-cyber-blue" />
            工作标准管理
          </h1>
          <p className="text-gray-400 mt-1">定义和管理各AI员工的工作质量、效率和专业标准</p>
        </div>
      </div>

      {/* 标准卡片列表 */}
      {standards.length === 0 ? (
        <div className="bg-dark-purple/40 rounded-xl p-12 text-center">
          <ClipboardCheck className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg">暂无工作标准数据</p>
          <p className="text-gray-500 text-sm mt-2">系统启动后会自动创建默认标准</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(groupedStandards).map(([agentType, agentStandards]) => (
            <div
              key={agentType}
              className="bg-dark-purple/40 rounded-xl overflow-hidden"
            >
              {/* 标题栏 */}
              <button
                onClick={() => toggleExpand(agentType)}
                className="w-full flex items-center justify-between p-5 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyber-blue to-cyber-purple flex items-center justify-center">
                    <Bot className="w-6 h-6 text-white" />
                  </div>
                  <div className="text-left">
                    <h3 className="text-white font-semibold text-lg">
                      {agentNames[agentType] || agentType}
                    </h3>
                    <p className="text-gray-400 text-sm">{agentType} · {agentStandards.length} 个标准</p>
                  </div>
                </div>
                {expandedAgent === agentType ? (
                  <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
              </button>

              {/* 展开内容 */}
              <AnimatePresence>
                {expandedAgent === agentType && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="px-5 pb-5 pt-2 border-t border-gray-800">
                      {agentStandards.map(standard => (
                        <div key={standard.id} className="mb-6 last:mb-0">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="text-white font-medium flex items-center gap-2">
                              {standard.standard_name}
                              <span className="text-xs text-gray-500">v{standard.version}</span>
                            </h4>
                            <button
                              onClick={() => setEditingStandard(standard)}
                              className="flex items-center gap-2 px-4 py-2 text-cyber-blue hover:bg-cyber-blue/10 rounded-lg transition-colors"
                            >
                              <Edit2 className="w-4 h-4" />
                              编辑标准
                            </button>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* 标准内容 */}
                            <div className="bg-deep-space/50 rounded-xl p-4">
                              <div className="flex items-center gap-2 mb-4">
                                <Award className="w-5 h-5 text-green-400" />
                                <h4 className="text-white font-medium">标准内容</h4>
                              </div>
                              <div className="space-y-3">
                                {Object.entries(standard.standard_content).map(([key, value]) => (
                                  <div key={key}>
                                    <p className="text-gray-500 text-xs mb-1">
                                      {key.replace(/_/g, ' ')}
                                    </p>
                                    <p className="text-white text-sm">{renderValue(value)}</p>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* 质量指标 */}
                            <div className="bg-deep-space/50 rounded-xl p-4">
                              <div className="flex items-center gap-2 mb-4">
                                <Zap className="w-5 h-5 text-yellow-400" />
                                <h4 className="text-white font-medium">质量指标</h4>
                              </div>
                              <div className="space-y-3">
                                {Object.entries(standard.quality_metrics).map(([key, value]) => (
                                  <div key={key}>
                                    <p className="text-gray-500 text-xs mb-1">
                                      {key.replace(/_/g, ' ')}
                                    </p>
                                    <p className="text-white text-sm">{renderValue(value)}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      )}

      {/* 编辑弹窗 */}
      <AnimatePresence>
        {editingStandard && (
          <EditStandardModal
            standard={editingStandard}
            onClose={() => setEditingStandard(null)}
            onSave={handleUpdateStandard}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
