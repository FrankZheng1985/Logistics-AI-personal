'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowLeft,
  Plus,
  Play,
  Download,
  Trash2,
  Clock,
  CheckCircle,
  AlertCircle,
  Film,
  Loader2,
  RefreshCw,
  X
} from 'lucide-react'
import Link from 'next/link'

interface Video {
  id: string
  title: string
  type: string
  status: 'draft' | 'generating' | 'completed' | 'failed'
  duration: number | null
  createdAt: string
  thumbnailUrl: string | null
  videoUrl: string | null
}

// 视频状态配置
const statusConfig = {
  draft: { label: '草稿', color: 'text-gray-400', bg: 'bg-gray-500/20', icon: Clock },
  generating: { label: '生成中', color: 'text-energy-orange', bg: 'bg-energy-orange/20', icon: Clock },
  completed: { label: '已完成', color: 'text-cyber-green', bg: 'bg-cyber-green/20', icon: CheckCircle },
  failed: { label: '失败', color: 'text-alert-red', bg: 'bg-alert-red/20', icon: AlertCircle },
}

// 视频卡片
function VideoCard({ 
  video, 
  onDownload, 
  onDelete, 
  onRegenerate,
  onPlay 
}: { 
  video: Video
  onDownload: () => void
  onDelete: () => void
  onRegenerate: () => void
  onPlay: () => void
}) {
  const status = statusConfig[video.status as keyof typeof statusConfig]
  const StatusIcon = status.icon
  const [deleting, setDeleting] = useState(false)
  const [regenerating, setRegenerate] = useState(false)
  
  const handleDelete = async () => {
    if (!confirm('确定要删除这个视频吗？')) return
    setDeleting(true)
    await onDelete()
    setDeleting(false)
  }
  
  const handleRegenerate = async () => {
    setRegenerate(true)
    await onRegenerate()
    setRegenerate(false)
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      className="glass-card overflow-hidden group"
    >
      {/* 缩略图 */}
      <div className="relative aspect-video bg-gradient-to-br from-dark-purple to-cyber-blue/20">
        {video.thumbnailUrl ? (
          <img src={video.thumbnailUrl} alt={video.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Film className="w-12 h-12 text-gray-600" />
          </div>
        )}
        
        {/* 播放按钮 */}
        {video.status === 'completed' && video.videoUrl && (
          <button 
            onClick={onPlay}
            className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <div className="w-14 h-14 rounded-full bg-cyber-blue/80 flex items-center justify-center hover:bg-cyber-blue transition-colors">
              <Play className="w-6 h-6 text-white ml-1" />
            </div>
          </button>
        )}
        
        {/* 时长 */}
        {video.duration && (
          <span className="absolute bottom-2 right-2 px-2 py-1 bg-black/70 rounded text-xs font-number">
            {Math.floor(video.duration / 60)}:{(video.duration % 60).toString().padStart(2, '0')}
          </span>
        )}
        
        {/* 状态 */}
        <span className={`absolute top-2 left-2 px-2 py-1 rounded-full text-xs flex items-center gap-1 ${status.bg} ${status.color}`}>
          <StatusIcon className="w-3 h-3" />
          {status.label}
        </span>
      </div>
      
      {/* 信息 */}
      <div className="p-4">
        <h3 className="font-medium mb-1 truncate">{video.title}</h3>
        <p className="text-gray-500 text-sm mb-3">{video.type} · {video.createdAt}</p>
        
        {/* 操作按钮 */}
        <div className="flex items-center gap-2">
          {video.status === 'completed' && (
            <>
              <button 
                onClick={onDownload}
                disabled={!video.videoUrl}
                className="flex-1 py-2 px-3 glass-card hover:border-cyber-blue/50 transition-colors text-sm flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download className="w-4 h-4" />
                下载
              </button>
              <button 
                onClick={handleDelete}
                disabled={deleting}
                className="p-2 glass-card hover:border-alert-red/50 hover:text-alert-red transition-colors disabled:opacity-50"
              >
                {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              </button>
            </>
          )}
          {video.status === 'generating' && (
            <div className="flex-1 py-2 px-3 text-center text-sm text-energy-orange">
              <Loader2 className="w-4 h-4 inline mr-1 animate-spin" />
              生成中...
            </div>
          )}
          {video.status === 'failed' && (
            <button 
              onClick={handleRegenerate}
              disabled={regenerating}
              className="flex-1 py-2 px-3 glass-card hover:border-cyber-blue/50 transition-colors text-sm flex items-center justify-center gap-1 disabled:opacity-50"
            >
              {regenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              重新生成
            </button>
          )}
          {video.status === 'draft' && (
            <button 
              onClick={handleRegenerate}
              disabled={regenerating}
              className="flex-1 py-2 px-3 glass-card hover:border-cyber-blue/50 transition-colors text-sm flex items-center justify-center gap-1 disabled:opacity-50"
            >
              {regenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              开始生成
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// 视频播放弹窗
function VideoModal({ video, onClose }: { video: Video | null, onClose: () => void }) {
  if (!video || !video.videoUrl) return null
  
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      onClick={onClose}
    >
      <motion.div 
        initial={{ scale: 0.9 }}
        animate={{ scale: 1 }}
        className="relative w-full max-w-4xl mx-4"
        onClick={e => e.stopPropagation()}
      >
        <button 
          onClick={onClose}
          className="absolute -top-12 right-0 p-2 text-white hover:text-cyber-blue transition-colors"
        >
          <X className="w-6 h-6" />
        </button>
        <div className="glass-card overflow-hidden">
          <video 
            src={video.videoUrl} 
            controls 
            autoPlay 
            className="w-full aspect-video"
          />
          <div className="p-4">
            <h3 className="text-lg font-medium">{video.title}</h3>
            <p className="text-gray-400 text-sm">{video.type} · {video.createdAt}</p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default function VideosPage() {
  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [playingVideo, setPlayingVideo] = useState<Video | null>(null)
  
  const fetchVideos = async () => {
    try {
      const res = await fetch('/api/videos')
      if (res.ok) {
        const data = await res.json()
        if (data.items && data.items.length > 0) {
          const mapped = data.items.map((v: any) => ({
            id: v.id,
            title: v.title || '未命名视频',
            type: v.video_type || '广告视频',
            status: v.status || 'draft',
            duration: v.duration,
            createdAt: v.created_at ? formatTime(v.created_at) : '未知时间',
            thumbnailUrl: v.thumbnail_url,
            videoUrl: v.video_url
          }))
          setVideos(mapped)
          setTotal(data.total || mapped.length)
        } else {
          setVideos([])
          setTotal(0)
        }
      }
    } catch (error) {
      console.error('获取视频列表失败:', error)
      setVideos([])
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => {
    setLoading(true)
    fetchVideos()
    const interval = setInterval(fetchVideos, 30000)
    return () => clearInterval(interval)
  }, [])
  
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diff < 3600) return '今天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    if (diff < 86400) return '今天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    if (diff < 172800) return '昨天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    return date.toLocaleDateString('zh-CN')
  }
  
  const handleDownload = (video: Video) => {
    if (!video.videoUrl) {
      alert('视频文件不存在')
      return
    }
    // 创建下载链接
    const a = document.createElement('a')
    a.href = video.videoUrl
    a.download = `${video.title}.mp4`
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
  
  const handleDelete = async (videoId: string) => {
    try {
      const res = await fetch(`/api/videos/${videoId}`, { method: 'DELETE' })
      if (res.ok) {
        setVideos(prev => prev.filter(v => v.id !== videoId))
        setTotal(prev => prev - 1)
      } else {
        alert('删除失败，请重试')
      }
    } catch (error) {
      console.error('删除视频失败:', error)
      alert('删除失败，请重试')
    }
  }
  
  const handleRegenerate = async (video: Video) => {
    try {
      const res = await fetch(`/api/videos/${video.id}/regenerate`, { method: 'POST' })
      if (res.ok) {
        // 刷新列表
        await fetchVideos()
        alert('视频重新生成任务已创建，请等待3-5分钟后刷新查看')
      } else {
        alert('重新生成失败，请重试')
      }
    } catch (error) {
      console.error('重新生成失败:', error)
      alert('重新生成失败，请重试')
    }
  }
  
  const completedCount = videos.filter(v => v.status === 'completed').length
  const generatingCount = videos.filter(v => v.status === 'generating').length
  const failedCount = videos.filter(v => v.status === 'failed').length
  
  return (
    <div className="min-h-screen p-6">
      {/* 头部 */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="p-2 glass-card hover:border-cyber-blue/50 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">视频中心</h1>
            <p className="text-gray-400 text-sm">管理AI生成的视频内容</p>
          </div>
        </div>
        <Link href="/videos/create" className="btn-cyber flex items-center gap-2">
          <Plus className="w-4 h-4" />
          生成新视频
        </Link>
      </header>
      
      {/* 统计 */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="glass-card p-4 text-center">
          {loading ? <Loader2 className="w-8 h-8 animate-spin text-cyber-blue mx-auto" /> : (
            <p className="text-3xl font-number font-bold text-cyber-blue">{total}</p>
          )}
          <p className="text-gray-500 text-sm">总视频数</p>
        </div>
        <div className="glass-card p-4 text-center">
          {loading ? <Loader2 className="w-8 h-8 animate-spin text-cyber-green mx-auto" /> : (
            <p className="text-3xl font-number font-bold text-cyber-green">{completedCount}</p>
          )}
          <p className="text-gray-500 text-sm">已完成</p>
        </div>
        <div className="glass-card p-4 text-center">
          {loading ? <Loader2 className="w-8 h-8 animate-spin text-energy-orange mx-auto" /> : (
            <p className="text-3xl font-number font-bold text-energy-orange">{generatingCount}</p>
          )}
          <p className="text-gray-500 text-sm">生成中</p>
        </div>
        <div className="glass-card p-4 text-center">
          {loading ? <Loader2 className="w-8 h-8 animate-spin text-alert-red mx-auto" /> : (
            <p className="text-3xl font-number font-bold text-alert-red">{failedCount}</p>
          )}
          <p className="text-gray-500 text-sm">失败</p>
        </div>
      </div>
      
      {/* 视频网格 */}
      {loading ? (
        <div className="glass-card p-12 text-center">
          <Loader2 className="w-10 h-10 animate-spin text-cyber-blue mx-auto mb-4" />
          <p className="text-gray-400">加载视频数据...</p>
        </div>
      ) : videos.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Film className="w-16 h-16 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-400 text-lg mb-2">暂无视频</p>
          <p className="text-gray-500 text-sm mb-4">点击"生成新视频"开始创建AI视频</p>
          <Link href="/videos/create" className="btn-cyber inline-flex items-center gap-2">
            <Plus className="w-4 h-4" />
            生成第一个视频
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {videos.map((video, index) => (
            <motion.div
              key={video.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <VideoCard 
                video={video} 
                onDownload={() => handleDownload(video)}
                onDelete={() => handleDelete(video.id)}
                onRegenerate={() => handleRegenerate(video)}
                onPlay={() => setPlayingVideo(video)}
              />
            </motion.div>
          ))}
        </div>
      )}
      
      {/* 视频播放弹窗 */}
      {playingVideo && (
        <VideoModal video={playingVideo} onClose={() => setPlayingVideo(null)} />
      )}
    </div>
  )
}
