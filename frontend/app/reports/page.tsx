'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  BarChart3,
  TrendingUp,
  Users,
  MessageSquare,
  Video,
  Target,
  RefreshCw,
  Loader2,
  Calendar,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import Link from 'next/link'

interface OverviewData {
  period_days: number
  leads: {
    total: number
    today: number
    converted: number
    conversion_rate: number
  }
  customers: {
    total: number
    today: number
    high_intent: number
  }
  conversations: {
    total: number
    inbound: number
    outbound: number
  }
  videos: {
    total: number
    success: number
  }
}

interface FunnelStage {
  stage: string
  name: string
  count: number
  conversion_rate: number
}

interface ChannelData {
  channel: string
  channel_name: string
  lead_count: number
  converted_count: number
  conversion_rate: number
  avg_quality_score: number
}

export default function ReportsPage() {
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState(7)
  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [funnel, setFunnel] = useState<FunnelStage[]>([])
  const [channels, setChannels] = useState<ChannelData[]>([])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [overviewRes, funnelRes, channelsRes] = await Promise.all([
        fetch(`/api/reports/overview?days=${period}`),
        fetch(`/api/reports/funnel?days=${period}`),
        fetch(`/api/reports/channels?days=${period}`)
      ])

      if (overviewRes.ok) setOverview(await overviewRes.json())
      if (funnelRes.ok) {
        const data = await funnelRes.json()
        setFunnel(data.funnel || [])
      }
      if (channelsRes.ok) {
        const data = await channelsRes.json()
        setChannels(data.channels || [])
      }
    } catch (error) {
      console.error('获取报表数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [period])

  return (
    <div className="min-h-screen p-6">
      {/* 头部 */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <BarChart3 className="w-7 h-7 text-cyber-blue" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
                数据报表
              </span>
            </h1>
            <p className="text-gray-400 text-sm">业务数据分析与转化漏斗</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* 时间范围选择 */}
          <div className="flex glass-card overflow-hidden">
            {[7, 14, 30].map(days => (
              <button
                key={days}
                onClick={() => setPeriod(days)}
                className={`px-4 py-2 text-sm transition-colors ${
                  period === days 
                    ? 'bg-cyber-blue/20 text-cyber-blue' 
                    : 'hover:bg-white/5 text-gray-400'
                }`}
              >
                {days}天
              </button>
            ))}
          </div>
          <button 
            onClick={fetchData}
            disabled={loading}
            className="p-2 glass-card hover:border-cyber-blue/50 transition-colors"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <RefreshCw className="w-5 h-5" />
            )}
          </button>
        </div>
      </header>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-cyber-blue" />
        </div>
      ) : (
        <>
          {/* 概览卡片 */}
          <div className="grid grid-cols-4 gap-4 mb-8">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <Target className="w-8 h-8 text-cyber-blue" />
                <span className="text-xs text-gray-500">近{period}天</span>
              </div>
              <p className="text-3xl font-number font-bold text-cyber-blue">
                {overview?.leads.total || 0}
              </p>
              <p className="text-gray-400 text-sm">总线索</p>
              <div className="mt-2 flex items-center text-xs">
                <span className="text-cyber-green flex items-center">
                  <ArrowUpRight className="w-3 h-3" />
                  今日 +{overview?.leads.today || 0}
                </span>
              </div>
            </motion.div>
            
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-card p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <Users className="w-8 h-8 text-neon-purple" />
                <span className="text-xs text-gray-500">近{period}天</span>
              </div>
              <p className="text-3xl font-number font-bold text-neon-purple">
                {overview?.customers.total || 0}
              </p>
              <p className="text-gray-400 text-sm">总客户</p>
              <div className="mt-2 flex items-center text-xs">
                <span className="text-energy-orange">
                  高意向: {overview?.customers.high_intent || 0}
                </span>
              </div>
            </motion.div>
            
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="glass-card p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <MessageSquare className="w-8 h-8 text-cyber-green" />
                <span className="text-xs text-gray-500">近{period}天</span>
              </div>
              <p className="text-3xl font-number font-bold text-cyber-green">
                {overview?.conversations.total || 0}
              </p>
              <p className="text-gray-400 text-sm">总对话</p>
              <div className="mt-2 flex items-center gap-2 text-xs">
                <span className="text-gray-500">入:{overview?.conversations.inbound || 0}</span>
                <span className="text-gray-500">出:{overview?.conversations.outbound || 0}</span>
              </div>
            </motion.div>
            
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="glass-card p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <TrendingUp className="w-8 h-8 text-energy-orange" />
                <span className="text-xs text-gray-500">转化率</span>
              </div>
              <p className="text-3xl font-number font-bold text-energy-orange">
                {overview?.leads.conversion_rate || 0}%
              </p>
              <p className="text-gray-400 text-sm">线索转化</p>
              <div className="mt-2 flex items-center text-xs">
                <span className="text-cyber-green">
                  已转化: {overview?.leads.converted || 0}
                </span>
              </div>
            </motion.div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* 转化漏斗 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="glass-card p-6"
            >
              <h2 className="text-lg font-bold mb-6 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-cyber-blue" />
                转化漏斗
              </h2>
              
              <div className="space-y-4">
                {funnel.map((stage, index) => {
                  const maxCount = funnel[0]?.count || 1
                  const width = (stage.count / maxCount) * 100
                  
                  return (
                    <div key={stage.stage}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-gray-300">{stage.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-number text-cyber-blue">{stage.count}</span>
                          {index > 0 && (
                            <span className="text-xs text-gray-500">
                              ({stage.conversion_rate}%)
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="h-8 bg-white/5 rounded overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${width}%` }}
                          transition={{ duration: 0.5, delay: index * 0.1 }}
                          className={`h-full ${
                            index === 0 ? 'bg-gradient-to-r from-cyber-blue to-cyber-blue/50' :
                            index === funnel.length - 1 ? 'bg-gradient-to-r from-cyber-green to-cyber-green/50' :
                            'bg-gradient-to-r from-neon-purple to-neon-purple/50'
                          }`}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
              
              {funnel.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  暂无漏斗数据
                </div>
              )}
            </motion.div>

            {/* 渠道分析 */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="glass-card p-6"
            >
              <h2 className="text-lg font-bold mb-6 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-neon-purple" />
                渠道分析
              </h2>
              
              <div className="space-y-4">
                {channels.map((channel, index) => (
                  <motion.div
                    key={channel.channel}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="p-4 bg-white/5 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{channel.channel_name}</span>
                      <span className="text-cyber-blue font-number">{channel.lead_count} 条线索</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-gray-500">
                        转化: <span className="text-cyber-green">{channel.converted_count}</span>
                      </span>
                      <span className="text-gray-500">
                        转化率: <span className="text-energy-orange">{channel.conversion_rate}%</span>
                      </span>
                      <span className="text-gray-500">
                        质量分: <span className="text-neon-purple">{channel.avg_quality_score}</span>
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
              
              {channels.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  暂无渠道数据
                </div>
              )}
            </motion.div>
          </div>

          {/* 快捷链接 */}
          <div className="mt-8 grid grid-cols-4 gap-4">
            <Link href="/team" className="glass-card p-4 hover:border-cyber-blue/50 transition-colors flex items-center gap-3">
              <Users className="w-5 h-5 text-cyber-blue" />
              <span>AI员工报表</span>
            </Link>
            <Link href="/leads" className="glass-card p-4 hover:border-neon-purple/50 transition-colors flex items-center gap-3">
              <Target className="w-5 h-5 text-neon-purple" />
              <span>线索管理</span>
            </Link>
            <Link href="/customers" className="glass-card p-4 hover:border-cyber-green/50 transition-colors flex items-center gap-3">
              <Users className="w-5 h-5 text-cyber-green" />
              <span>客户管理</span>
            </Link>
            <Link href="/videos" className="glass-card p-4 hover:border-energy-orange/50 transition-colors flex items-center gap-3">
              <Video className="w-5 h-5 text-energy-orange" />
              <span>视频管理</span>
            </Link>
          </div>
        </>
      )}
    </div>
  )
}
