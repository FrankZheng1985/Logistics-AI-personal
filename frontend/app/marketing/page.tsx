'use client'

import { useState } from 'react'
import { Mail, Plus, Play, Pause, Edit2, Trash2, Users, Clock, TrendingUp } from 'lucide-react'

interface MarketingSequence {
  id: string
  name: string
  description: string
  trigger: string
  status: 'active' | 'paused' | 'draft'
  email_count: number
  enrolled_count: number
  conversion_rate: number
  created_at: string
}

const mockSequences: MarketingSequence[] = [
  {
    id: '1',
    name: '新客户欢迎序列',
    description: '当新客户首次询价后自动触发的欢迎邮件序列',
    trigger: '首次询价',
    status: 'active',
    email_count: 5,
    enrolled_count: 234,
    conversion_rate: 12.5,
    created_at: '2025-12-01'
  },
  {
    id: '2',
    name: '报价跟进序列',
    description: '报价后未回复的客户自动跟进',
    trigger: '报价后3天未回复',
    status: 'active',
    email_count: 4,
    enrolled_count: 156,
    conversion_rate: 8.3,
    created_at: '2025-12-10'
  },
  {
    id: '3',
    name: '老客户激活序列',
    description: '30天未联系的老客户重新激活',
    trigger: '30天未联系',
    status: 'paused',
    email_count: 3,
    enrolled_count: 89,
    conversion_rate: 5.6,
    created_at: '2025-12-15'
  },
  {
    id: '4',
    name: '节日促销序列',
    description: '春节期间的促销活动邮件',
    trigger: '手动触发',
    status: 'draft',
    email_count: 2,
    enrolled_count: 0,
    conversion_rate: 0,
    created_at: '2026-01-10'
  }
]

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

export default function MarketingPage() {
  const [sequences] = useState<MarketingSequence[]>(mockSequences)

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
        <button className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity">
          <Plus className="w-4 h-4" />
          创建序列
        </button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-dark-card rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-400/10 rounded-lg">
              <Mail className="w-5 h-5 text-blue-400" />
            </div>
            <span className="text-gray-400">总序列数</span>
          </div>
          <p className="text-2xl font-bold text-white">{sequences.length}</p>
        </div>
        <div className="bg-dark-card rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-green-400/10 rounded-lg">
              <Play className="w-5 h-5 text-green-400" />
            </div>
            <span className="text-gray-400">运行中</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {sequences.filter(s => s.status === 'active').length}
          </p>
        </div>
        <div className="bg-dark-card rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-purple-400/10 rounded-lg">
              <Users className="w-5 h-5 text-purple-400" />
            </div>
            <span className="text-gray-400">总触达人数</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {sequences.reduce((sum, s) => sum + s.enrolled_count, 0)}
          </p>
        </div>
        <div className="bg-dark-card rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-cyan-400/10 rounded-lg">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
            </div>
            <span className="text-gray-400">平均转化率</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {(sequences.filter(s => s.enrolled_count > 0).reduce((sum, s) => sum + s.conversion_rate, 0) / sequences.filter(s => s.enrolled_count > 0).length || 0).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* 序列列表 */}
      <div className="space-y-4">
        {sequences.map(sequence => (
          <div
            key={sequence.id}
            className="bg-dark-card rounded-xl p-5 hover:ring-1 hover:ring-cyber-blue/50 transition-all"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-white font-semibold text-lg">{sequence.name}</h3>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${statusColors[sequence.status]}`}>
                    {statusNames[sequence.status]}
                  </span>
                </div>
                <p className="text-gray-400 text-sm mb-4">{sequence.description}</p>
                
                <div className="flex items-center gap-6 text-sm">
                  <div className="flex items-center gap-2 text-gray-500">
                    <Clock className="w-4 h-4" />
                    <span>触发条件: {sequence.trigger}</span>
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
                  <button className="p-2 text-yellow-400 hover:bg-yellow-400/10 rounded-lg transition-colors" title="暂停">
                    <Pause className="w-5 h-5" />
                  </button>
                ) : sequence.status === 'paused' ? (
                  <button className="p-2 text-green-400 hover:bg-green-400/10 rounded-lg transition-colors" title="启动">
                    <Play className="w-5 h-5" />
                  </button>
                ) : null}
                <button className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors" title="编辑">
                  <Edit2 className="w-5 h-5" />
                </button>
                <button className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors" title="删除">
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
