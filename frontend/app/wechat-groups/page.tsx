'use client'

import { useState } from 'react'
import { MessageCircle, Users, TrendingUp, Target, Eye, EyeOff, Plus, Search } from 'lucide-react'

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

const mockGroups: WechatGroup[] = [
  {
    id: '1',
    name: '深圳货代同行交流群',
    member_count: 456,
    is_monitoring: true,
    messages_today: 234,
    leads_found: 5,
    intel_count: 12,
    last_activity: '2分钟前'
  },
  {
    id: '2',
    name: '亚马逊卖家物流群',
    member_count: 312,
    is_monitoring: true,
    messages_today: 178,
    leads_found: 8,
    intel_count: 6,
    last_activity: '5分钟前'
  },
  {
    id: '3',
    name: '跨境电商交流群',
    member_count: 523,
    is_monitoring: true,
    messages_today: 89,
    leads_found: 3,
    intel_count: 4,
    last_activity: '15分钟前'
  },
  {
    id: '4',
    name: '外贸SOHO互助群',
    member_count: 234,
    is_monitoring: false,
    messages_today: 0,
    leads_found: 0,
    intel_count: 0,
    last_activity: '已暂停'
  }
]

const mockMessages: GroupMessage[] = [
  {
    id: '1',
    group_name: '亚马逊卖家物流群',
    sender: '王老板',
    content: '有没有做FBA头程的货代推荐？货量比较大，一个月大概20个柜',
    category: 'lead',
    time: '10:23'
  },
  {
    id: '2',
    group_name: '深圳货代同行交流群',
    sender: '李总',
    content: '最新消息：欧洲航线下周开始涨价，涨幅大概15%左右',
    category: 'intel',
    time: '10:18'
  },
  {
    id: '3',
    group_name: '深圳货代同行交流群',
    sender: '张经理',
    content: '分享个经验：敏感货走香港中转比较稳，虽然贵一点但是安全',
    category: 'knowledge',
    time: '10:15'
  }
]

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
  const [groups] = useState<WechatGroup[]>(mockGroups)
  const [messages] = useState<GroupMessage[]>(mockMessages)
  const [searchQuery, setSearchQuery] = useState('')

  const totalLeads = groups.reduce((sum, g) => sum + g.leads_found, 0)
  const totalIntel = groups.reduce((sum, g) => sum + g.intel_count, 0)
  const activeGroups = groups.filter(g => g.is_monitoring).length

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
        <button className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity">
          <Plus className="w-4 h-4" />
          添加群组
        </button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-dark-card rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-400/10 rounded-lg">
              <Users className="w-5 h-5 text-blue-400" />
            </div>
            <span className="text-gray-400">监控群组</span>
          </div>
          <p className="text-2xl font-bold text-white">{activeGroups}/{groups.length}</p>
        </div>
        <div className="bg-dark-card rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-green-400/10 rounded-lg">
              <Target className="w-5 h-5 text-green-400" />
            </div>
            <span className="text-gray-400">今日发现线索</span>
          </div>
          <p className="text-2xl font-bold text-white">{totalLeads}</p>
        </div>
        <div className="bg-dark-card rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-purple-400/10 rounded-lg">
              <TrendingUp className="w-5 h-5 text-purple-400" />
            </div>
            <span className="text-gray-400">今日情报</span>
          </div>
          <p className="text-2xl font-bold text-white">{totalIntel}</p>
        </div>
        <div className="bg-dark-card rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-cyan-400/10 rounded-lg">
              <MessageCircle className="w-5 h-5 text-cyan-400" />
            </div>
            <span className="text-gray-400">今日消息</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {groups.reduce((sum, g) => sum + g.messages_today, 0)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 群组列表 */}
        <div className="bg-dark-card rounded-xl p-5">
          <h2 className="text-lg font-semibold text-white mb-4">监控群组</h2>
          <div className="space-y-3">
            {groups.map(group => (
              <div
                key={group.id}
                className="flex items-center justify-between p-4 bg-dark-bg rounded-lg hover:ring-1 hover:ring-cyber-blue/30 transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${group.is_monitoring ? 'bg-green-400/10' : 'bg-gray-400/10'}`}>
                    <MessageCircle className={`w-5 h-5 ${group.is_monitoring ? 'text-green-400' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <p className="text-white font-medium">{group.name}</p>
                    <p className="text-gray-500 text-xs">{group.member_count} 人 · {group.last_activity}</p>
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
                    className={`p-2 rounded-lg transition-colors ${
                      group.is_monitoring 
                        ? 'text-green-400 hover:bg-green-400/10' 
                        : 'text-gray-500 hover:bg-white/10'
                    }`}
                  >
                    {group.is_monitoring ? <Eye className="w-5 h-5" /> : <EyeOff className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 最新提取信息 */}
        <div className="bg-dark-card rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">最新提取信息</h2>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="搜索..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 bg-dark-bg border border-gray-700 rounded-lg text-white text-sm focus:border-cyber-blue focus:outline-none w-40"
              />
            </div>
          </div>
          <div className="space-y-3">
            {messages.map(msg => (
              <div
                key={msg.id}
                className="p-4 bg-dark-bg rounded-lg"
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
        </div>
      </div>
    </div>
  )
}
