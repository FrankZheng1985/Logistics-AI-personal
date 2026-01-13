'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowLeft,
  Video,
  Sparkles,
  Loader2,
  CheckCircle
} from 'lucide-react'
import Link from 'next/link'

// 视频类型选项
const videoTypes = [
  { id: 'ad', label: '广告视频', desc: '短视频广告，吸引客户关注' },
  { id: 'intro', label: '服务介绍', desc: '详细介绍物流服务内容' },
  { id: 'route', label: '航线展示', desc: '展示热门航线和时效' },
  { id: 'brand', label: '品牌宣传', desc: '公司形象和实力展示' },
]

export default function CreateVideoPage() {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [videoType, setVideoType] = useState('ad')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationStep, setGenerationStep] = useState(0)
  
  const steps = [
    { label: '小调分配任务', agent: '小调' },
    { label: '小文撰写脚本', agent: '小文' },
    { label: '小视生成视频', agent: '小视' },
    { label: '完成', agent: '' },
  ]
  
  const handleGenerate = async () => {
    if (!title) return
    
    setIsGenerating(true)
    
    // 模拟生成过程
    for (let i = 0; i < steps.length; i++) {
      setGenerationStep(i)
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
    
    // 完成后跳转
    // router.push('/videos')
  }
  
  return (
    <div className="min-h-screen p-6">
      {/* 头部 */}
      <header className="flex items-center gap-4 mb-8">
        <Link href="/videos" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Video className="w-6 h-6 text-cyber-blue" />
            生成新视频
          </h1>
          <p className="text-gray-400 text-sm">AI员工将自动为你创作视频内容</p>
        </div>
      </header>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* 左侧：表单 */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="space-y-6"
        >
          {/* 视频标题 */}
          <div>
            <label className="block text-sm font-medium mb-2">视频标题</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如：海运物流服务宣传片"
              className="w-full px-4 py-3 bg-dark-purple/50 border border-white/10 rounded-lg focus:border-cyber-blue/50 focus:outline-none transition-colors"
              disabled={isGenerating}
            />
          </div>
          
          {/* 视频描述 */}
          <div>
            <label className="block text-sm font-medium mb-2">视频描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="描述你希望视频展示的内容、卖点、风格等..."
              rows={4}
              className="w-full px-4 py-3 bg-dark-purple/50 border border-white/10 rounded-lg focus:border-cyber-blue/50 focus:outline-none transition-colors resize-none"
              disabled={isGenerating}
            />
          </div>
          
          {/* 视频类型 */}
          <div>
            <label className="block text-sm font-medium mb-2">视频类型</label>
            <div className="grid grid-cols-2 gap-3">
              {videoTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setVideoType(type.id)}
                  disabled={isGenerating}
                  className={`p-4 rounded-lg text-left transition-all ${
                    videoType === type.id
                      ? 'bg-cyber-blue/20 border-2 border-cyber-blue'
                      : 'glass-card hover:border-cyber-blue/30'
                  }`}
                >
                  <p className="font-medium">{type.label}</p>
                  <p className="text-gray-500 text-sm">{type.desc}</p>
                </button>
              ))}
            </div>
          </div>
          
          {/* 生成按钮 */}
          <button
            onClick={handleGenerate}
            disabled={!title || isGenerating}
            className="w-full btn-cyber py-4 text-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                生成中...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                开始生成
              </>
            )}
          </button>
        </motion.div>
        
        {/* 右侧：生成进度 */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-card p-6"
        >
          <h2 className="text-lg font-bold mb-6">生成流程</h2>
          
          <div className="space-y-4">
            {steps.map((step, index) => (
              <div
                key={index}
                className={`flex items-center gap-4 p-4 rounded-lg transition-all ${
                  isGenerating && generationStep === index
                    ? 'bg-cyber-blue/20 border border-cyber-blue/50'
                    : isGenerating && generationStep > index
                    ? 'bg-cyber-green/10 border border-cyber-green/30'
                    : 'bg-white/5'
                }`}
              >
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  isGenerating && generationStep > index
                    ? 'bg-cyber-green'
                    : isGenerating && generationStep === index
                    ? 'bg-cyber-blue animate-pulse'
                    : 'bg-gray-700'
                }`}>
                  {isGenerating && generationStep > index ? (
                    <CheckCircle className="w-5 h-5 text-black" />
                  ) : isGenerating && generationStep === index ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <span className="font-number">{index + 1}</span>
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-medium">{step.label}</p>
                  {step.agent && (
                    <p className="text-gray-500 text-sm">由 {step.agent} 处理</p>
                  )}
                </div>
                {isGenerating && generationStep === index && (
                  <span className="text-cyber-blue text-sm">处理中...</span>
                )}
              </div>
            ))}
          </div>
          
          {/* 提示信息 */}
          <div className="mt-6 p-4 bg-neon-purple/10 border border-neon-purple/30 rounded-lg">
            <p className="text-sm text-gray-300">
              <Sparkles className="w-4 h-4 inline mr-1 text-neon-purple" />
              视频生成大约需要 1-3 分钟，完成后会通知你。
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
