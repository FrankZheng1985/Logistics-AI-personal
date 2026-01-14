'use client'

import { useState } from 'react'
import { ClipboardCheck, Bot, Zap, Award, ChevronDown, ChevronUp, Edit2 } from 'lucide-react'

interface AgentStandard {
  agent_type: string
  agent_name: string
  standards: {
    quality: Record<string, any>
    efficiency: Record<string, any>
    professional: Record<string, any>
  }
}

const mockStandards: AgentStandard[] = [
  {
    agent_type: 'video_creator',
    agent_name: '小影',
    standards: {
      quality: {
        video_duration: { min: '1.5分钟', max: '5分钟' },
        resolution: '1080p/4K',
        requirements: ['无水印', '无AI生成痕迹', '画面稳定流畅', '色彩专业统一']
      },
      efficiency: {
        short_video_time: '15分钟内',
        long_video_time: '30分钟内',
        max_retries: 3
      },
      professional: {
        supported_languages: 10,
        video_types: 5
      }
    }
  },
  {
    agent_type: 'copywriter',
    agent_name: '小文',
    standards: {
      quality: {
        originality_rate: '≥95%',
        grammar_error_rate: '0%',
        requirements: ['原创度高', '无语法错误', '情感共鸣强', '行动号召明确']
      },
      efficiency: {
        short_copy_time: '5分钟内',
        long_copy_time: '15分钟内',
        script_time: '20分钟内'
      },
      professional: {
        writing_models: ['AIDA', 'PAS', 'BAB', '4P', 'QUEST'],
        supported_languages: 8
      }
    }
  },
  {
    agent_type: 'coordinator',
    agent_name: '小调',
    standards: {
      quality: {
        report_accuracy: '≥99%',
        requirements: ['数据准确无误', '分析深入专业', '建议可执行']
      },
      efficiency: {
        daily_report_time: '5分钟内',
        task_dispatch_time: '3秒内'
      },
      professional: {
        report_types: ['日报', '周报', '月报'],
        monitoring_scope: ['API可用性', '证书有效期', '数据库状态']
      }
    }
  },
  {
    agent_type: 'sales',
    agent_name: '小销',
    standards: {
      quality: {
        satisfaction_rate: '≥90%',
        requirements: ['专业友好', '回复准确', '耐心细致', '善于引导']
      },
      efficiency: {
        first_response: '3秒内',
        avg_response: '10秒内',
        resolution_rate: '≥85%'
      },
      professional: {
        knowledge_areas: 6,
        info_collection_targets: 6
      }
    }
  },
  {
    agent_type: 'analyst',
    agent_name: '小析',
    standards: {
      quality: {
        intent_accuracy: '≥85%',
        requirements: ['评分准确客观', '画像全面深入', '洞察有价值']
      },
      efficiency: {
        real_time_analysis: '是',
        profile_generation: '2分钟内'
      },
      professional: {
        intent_levels: 4,
        profile_dimensions: 5
      }
    }
  },
  {
    agent_type: 'lead_hunter',
    agent_name: '小猎',
    standards: {
      quality: {
        min_quality_score: '≥60分',
        requirements: ['真实有效需求', '非广告/竞争对手', '可追踪联系']
      },
      efficiency: {
        daily_analysis: '≥50条',
        response_time: '5秒内'
      },
      professional: {
        search_sources: 4,
        high_intent_signals: 8
      }
    }
  }
]

export default function StandardsPage() {
  const [expandedAgent, setExpandedAgent] = useState<string | null>('video_creator')

  const toggleExpand = (agentType: string) => {
    setExpandedAgent(prev => prev === agentType ? null : agentType)
  }

  const renderValue = (value: any): string => {
    if (Array.isArray(value)) {
      return value.join('、')
    }
    if (typeof value === 'object') {
      return JSON.stringify(value)
    }
    return String(value)
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
      <div className="space-y-4">
        {mockStandards.map(agent => (
          <div
            key={agent.agent_type}
            className="bg-dark-card rounded-xl overflow-hidden"
          >
            {/* 标题栏 */}
            <button
              onClick={() => toggleExpand(agent.agent_type)}
              className="w-full flex items-center justify-between p-5 hover:bg-white/5 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyber-blue to-cyber-purple flex items-center justify-center">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div className="text-left">
                  <h3 className="text-white font-semibold text-lg">{agent.agent_name}</h3>
                  <p className="text-gray-400 text-sm">{agent.agent_type}</p>
                </div>
              </div>
              {expandedAgent === agent.agent_type ? (
                <ChevronUp className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              )}
            </button>

            {/* 展开内容 */}
            {expandedAgent === agent.agent_type && (
              <div className="px-5 pb-5 pt-2 border-t border-gray-800">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* 质量标准 */}
                  <div className="bg-dark-bg rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-4">
                      <Award className="w-5 h-5 text-green-400" />
                      <h4 className="text-white font-medium">质量标准</h4>
                    </div>
                    <div className="space-y-3">
                      {Object.entries(agent.standards.quality).map(([key, value]) => (
                        <div key={key}>
                          <p className="text-gray-500 text-xs mb-1">
                            {key.replace(/_/g, ' ')}
                          </p>
                          <p className="text-white text-sm">{renderValue(value)}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 效率标准 */}
                  <div className="bg-dark-bg rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-4">
                      <Zap className="w-5 h-5 text-yellow-400" />
                      <h4 className="text-white font-medium">效率标准</h4>
                    </div>
                    <div className="space-y-3">
                      {Object.entries(agent.standards.efficiency).map(([key, value]) => (
                        <div key={key}>
                          <p className="text-gray-500 text-xs mb-1">
                            {key.replace(/_/g, ' ')}
                          </p>
                          <p className="text-white text-sm">{renderValue(value)}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 专业标准 */}
                  <div className="bg-dark-bg rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-4">
                      <ClipboardCheck className="w-5 h-5 text-blue-400" />
                      <h4 className="text-white font-medium">专业标准</h4>
                    </div>
                    <div className="space-y-3">
                      {Object.entries(agent.standards.professional).map(([key, value]) => (
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

                <div className="mt-4 flex justify-end">
                  <button className="flex items-center gap-2 px-4 py-2 text-cyber-blue hover:bg-cyber-blue/10 rounded-lg transition-colors">
                    <Edit2 className="w-4 h-4" />
                    编辑标准
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
