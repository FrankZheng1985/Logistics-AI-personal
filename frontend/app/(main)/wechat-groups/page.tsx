'use client'

import { useState, useEffect, useCallback } from 'react'
import { MessageCircle, Users, TrendingUp, Target, Eye, EyeOff, Plus, Search, RefreshCw, X } from 'lucide-react'

interface WechatGroup {
  id: string
  name: string
  member_count: number
  is_monitoring: boolean
  messages_today: number
  leads_found: number
  intel_count: number
  last_activity: string
}

interface GroupMessage {
  id: string
  group_name: string
  sender: string
  content: string
  category: 'lead' | 'intel' | 'knowledge' | 'irrelevant'
  time: string
}

interface Stats {
  active_groups: number
  total_groups: number
  total_leads: number
  total_intel: number
  total_messages: number
}

const categoryColors = {
  lead: 'text-green-400 bg-green-400/10',
  intel: 'text-blue-400 bg-blue-400/10',
  knowledge: 'text-purple-400 bg-purple-400/10',
  irrelevant: 'text-gray-400 bg-gray-400/10'
}

const categoryNames = {
  lead: '潜在线索',
  intel: '行业情报',
  knowledge: '专业知识',
  irrelevant: '无关信息'
}

export default function WechatGroupsPage() {
  const [groups, setGroups] = useState<WechatGroup[]>([])
  const [messages, setMessages] = useState<GroupMessage[]>([])
  const [stats, setStats] = useState<Stats>({
    active_groups: 0,
    total_groups: 0,
    total_leads: 0,
    total_intel: 0,
    total_messages: 0
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      
      // 并行获取数据
      const [groupsRes, messagesRes, statsRes] = await Promise.all([
        fetch('/api/wechat-groups'),
        fetch('/api/wechat-groups/messages'),
        fetch('/api/wechat-groups/stats')
      ])

      if (groupsRes.ok) {
        const data = await groupsRes.json()
        setGroups(data.groups || [])
      }

      if (messagesRes.ok) {
        const data = await messagesRes.json()
        setMessages(data.messages || [])
      }

      if (statsRes.ok) {
        const data = await statsRes.json()
        setStats(data)
      }
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleToggleMonitoring = async (groupId: string) => {
    try {
      const res = await fetch(`/api/wechat-groups/${groupId}/toggle-monitoring`, {
        method: 'PUT'
      })
      if (res.ok) {
        const data = await res.json()
        setGroups(prev => prev.map(g => 
          g.id === groupId ? { ...g, is_monitoring: data.is_monitoring } : g
        ))
        // 刷新统计
        fetchData()
      }
    } catch (error) {
      console.error('切换监控状态失败:', error)
    }
  }

  const handleAddGroup = async () => {
    if (!newGroupName.trim()) return

    try {
      const res = await fetch('/api/wechat-groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newGroupName.trim() })
      })
      if (res.ok) {
        setNewGroupName('')
        setShowAddModal(false)
        fetchData()
      }
    } catch (error) {
      console.error('添加群组失败:', error)
    }
  }

  const filteredMessages = searchQuery
    ? messages.filter(m => 
        m.content.includes(searchQuery) || 
        m.sender.includes(searchQuery) ||
        m.group_name.includes(searchQuery)
      )
    : messages

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <MessageCircle className="w-7 h-7 text-cyber-blue" />
            微信群监控
          </h1>
          <p className="text-gray-400 mt-1">小析2静默监控微信群，自动提取有价值信息</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            title="刷新"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button 
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" />
            添加群组
          </button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-400/10 rounded-lg">
              <Users className="w-5 h-5 text-blue-400" />
            </div>
            <span className="text-gray-400">监控群组</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.active_groups}/{stats.total_groups}</p>
        </div>
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-green-400/10 rounded-lg">
              <Target className="w-5 h-5 text-green-400" />
            </div>
            <span className="text-gray-400">今日发现线索</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.total_leads}</p>
        </div>
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-purple-400/10 rounded-lg">
              <TrendingUp className="w-5 h-5 text-purple-400" />
            </div>
            <span className="text-gray-400">今日情报</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.total_intel}</p>
        </div>
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-cyan-400/10 rounded-lg">
              <MessageCircle className="w-5 h-5 text-cyan-400" />
            </div>
            <span className="text-gray-400">今日消息</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.total_messages}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 群组列表 */}
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <h2 className="text-lg font-semibold text-white mb-4">监控群组</h2>
          {loading ? (
            <div className="py-12 text-center">
              <RefreshCw className="w-8 h-8 text-cyber-blue mx-auto mb-4 animate-spin" />
              <p className="text-gray-400">加载中...</p>
            </div>
          ) : groups.length === 0 ? (
            <div className="py-12 text-center">
              <MessageCircle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">暂无监控群组</p>
              <p className="text-gray-500 text-sm mt-2">点击右上角添加群组开始监控</p>
            </div>
          ) : (
            <div className="space-y-3">
              {groups.map(group => (
                <div
                  key={group.id}
                  className="flex items-center justify-between p-4 bg-deep-space/50 rounded-lg hover:ring-1 hover:ring-cyber-blue/30 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${group.is_monitoring ? 'bg-green-400/10' : 'bg-gray-400/10'}`}>
                      <MessageCircle className={`w-5 h-5 ${group.is_monitoring ? 'text-green-400' : 'text-gray-400'}`} />
                    </div>
                    <div>
                      <p className="text-white font-medium">{group.name}</p>
                      <p className="text-gray-500 text-xs">{group.member_count} 人 · {group.last_activity || '未知'}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {group.is_monitoring && (
                      <div className="text-right">
                        <p className="text-green-400 text-sm">+{group.leads_found} 线索</p>
                        <p className="text-gray-500 text-xs">{group.messages_today} 消息</p>
                      </div>
                    )}
                    <button
                      onClick={() => handleToggleMonitoring(group.id)}
                      className={`p-2 rounded-lg transition-colors ${
                        group.is_monitoring 
                          ? 'text-green-400 hover:bg-green-400/10' 
                          : 'text-gray-500 hover:bg-white/10'
                      }`}
                      title={group.is_monitoring ? '暂停监控' : '开启监控'}
                    >
                      {group.is_monitoring ? <Eye className="w-5 h-5" /> : <EyeOff className="w-5 h-5" />}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 最新提取信息 */}
        <div className="bg-dark-purple/40 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">最新提取信息</h2>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="搜索..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 bg-deep-space/50 border border-gray-700 rounded-lg text-white text-sm focus:border-cyber-blue focus:outline-none w-40"
              />
            </div>
          </div>
          {loading ? (
            <div className="py-12 text-center">
              <RefreshCw className="w-8 h-8 text-cyber-blue mx-auto mb-4 animate-spin" />
              <p className="text-gray-400">加载中...</p>
            </div>
          ) : filteredMessages.length === 0 ? (
            <div className="py-12 text-center">
              <MessageCircle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">暂无消息记录</p>
              <p className="text-gray-500 text-sm mt-2">监控群组后会自动提取有价值信息</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredMessages.map(msg => (
                <div
                  key={msg.id}
                  className="p-4 bg-deep-space/50 rounded-lg"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 text-xs rounded-full ${categoryColors[msg.category]}`}>
                      {categoryNames[msg.category]}
                    </span>
                    <span className="text-gray-500 text-xs">{msg.group_name}</span>
                    <span className="text-gray-600 text-xs ml-auto">{msg.time}</span>
                  </div>
                  <p className="text-white text-sm mb-1">{msg.content}</p>
                  <p className="text-gray-500 text-xs">来自: {msg.sender}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 添加群组弹窗 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-dark-purple rounded-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">添加监控群组</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">群组名称</label>
                <input
                  type="text"
                  value={newGroupName}
                  onChange={e => setNewGroupName(e.target.value)}
                  placeholder="输入微信群名称"
                  className="w-full px-4 py-2 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                />
              </div>
              <p className="text-gray-500 text-sm">
                注：需要在企业微信后台配置相应的群组监控权限
              </p>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleAddGroup}
                  disabled={!newGroupName.trim()}
                  className="px-5 py-2 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  添加
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
