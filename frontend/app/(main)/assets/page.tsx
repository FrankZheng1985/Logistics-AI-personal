'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FolderOpen, Upload, Video, Music, Image, Grid, List, Play, Download, X, Loader2, Trash2, Sparkles, LogIn, LogOut, Check, AlertCircle, ExternalLink, QrCode, RefreshCw, Smartphone } from 'lucide-react'

interface Asset {
  id: string
  name: string
  type: 'video' | 'audio' | 'image'
  category: string
  duration?: number
  file_url?: string
  thumbnail_url?: string
  file_size: number
  usage_count: number
  created_at?: string
}

interface SocialPlatform {
  platform: string
  name: string
  is_logged_in: boolean
  username?: string
  avatar_url?: string
  expires_at?: string
  total_collected: number
  today_collected: number
  error_message?: string
}

const categories = [
  { id: 'all', name: '全部', icon: FolderOpen },
  { id: 'video', name: '视频素材', icon: Video },
  { id: 'audio', name: '背景音乐', icon: Music },
  { id: 'image', name: '图片素材', icon: Image }
]

const PLATFORM_ICONS: Record<string, string> = {
  xiaohongshu: '📕',
  douyin: '🎵',
  bilibili: '📺',
  pexels: '📷',
  pixabay: '🖼️'
}

const formatFileSize = (bytes: number) => {
  if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB'
  if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB'
  return (bytes / 1024).toFixed(1) + ' KB'
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 上传弹窗
function UploadModal({ onClose, onUpload }: { onClose: () => void; onUpload: () => void }) {
  const [uploading, setUploading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [category, setCategory] = useState('general')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUpload = async () => {
    if (!file) {
      alert('请选择文件')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (name) formData.append('name', name)
      formData.append('category', category)

      const res = await fetch('/api/assets/upload', {
        method: 'POST',
        body: formData
      })

      if (res.ok) {
        alert('上传成功！')
        onUpload()
        onClose()
      } else {
        const error = await res.json()
        alert(error.detail || '上传失败，请重试')
      }
    } catch (error) {
      console.error('上传失败:', error)
      alert('上传失败，请检查网络')
    } finally {
      setUploading(false)
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
          <h2 className="text-xl font-bold text-white">上传素材</h2>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* 文件选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">选择文件</label>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*,audio/*,image/*"
              onChange={e => {
                const f = e.target.files?.[0]
                if (f) {
                  setFile(f)
                  if (!name) setName(f.name.replace(/\.[^/.]+$/, ''))
                }
              }}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full p-8 border-2 border-dashed border-gray-600 rounded-xl text-center hover:border-cyber-blue/50 transition-colors"
            >
              {file ? (
                <div>
                  <p className="text-white font-medium">{file.name}</p>
                  <p className="text-gray-500 text-sm mt-1">{formatFileSize(file.size)}</p>
                </div>
              ) : (
                <div>
                  <Upload className="w-10 h-10 text-gray-500 mx-auto mb-2" />
                  <p className="text-gray-400">点击选择文件</p>
                  <p className="text-gray-500 text-sm mt-1">支持视频、音频、图片</p>
                </div>
              )}
            </button>
          </div>

          {/* 素材名称 */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">素材名称</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              placeholder="输入素材名称"
            />
          </div>

          {/* 分类 */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">分类</label>
            <select
              value={category}
              onChange={e => setCategory(e.target.value)}
              className="w-full px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
            >
              <option value="general">通用</option>
              <option value="port">港口</option>
              <option value="warehouse">仓库</option>
              <option value="truck">货运</option>
              <option value="airplane">航空</option>
              <option value="bgm_corporate">商务BGM</option>
              <option value="bgm_upbeat">动感BGM</option>
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
            onClick={handleUpload}
            disabled={uploading || !file}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {uploading && <Loader2 className="w-4 h-4 animate-spin" />}
            {uploading ? '上传中...' : '上传'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// 播放弹窗
function PlayModal({ asset, onClose }: { asset: Asset; onClose: () => void }) {
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
        className="w-full max-w-4xl mx-4"
        onClick={e => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-white hover:text-cyber-blue transition-colors"
        >
          <X className="w-6 h-6" />
        </button>

        <div className="bg-dark-purple/90 backdrop-blur-xl border border-white/10 rounded-xl overflow-hidden">
          {asset.type === 'video' && asset.file_url && (
            <video src={asset.file_url} controls autoPlay className="w-full aspect-video" />
          )}
          {asset.type === 'audio' && asset.file_url && (
            <div className="p-12 flex items-center justify-center">
              <audio src={asset.file_url} controls autoPlay className="w-full" />
            </div>
          )}
          {asset.type === 'image' && asset.file_url && (
            <img src={asset.file_url} alt={asset.name} className="w-full" />
          )}
          <div className="p-4">
            <h3 className="text-lg font-medium text-white">{asset.name}</h3>
            <p className="text-gray-400 text-sm mt-1">
              {asset.category} · {formatFileSize(asset.file_size)} · 使用 {asset.usage_count} 次
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// 扫码登录弹窗
function QRCodeLoginModal({ 
  platform, 
  platformName,
  onClose, 
  onSuccess 
}: { 
  platform: string
  platformName: string
  onClose: () => void
  onSuccess: () => void
}) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [qrImage, setQrImage] = useState<string | null>(null)
  const [status, setStatus] = useState<'loading' | 'waiting' | 'success' | 'error' | 'timeout'>('loading')
  const [message, setMessage] = useState('')
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // 开始扫码登录
  const startLogin = useCallback(async () => {
    setStatus('loading')
    setMessage('正在加载二维码...')
    
    try {
      const res = await fetch('/api/social-auth/qrcode/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform })
      })
      
      if (res.ok) {
        const data = await res.json()
        setSessionId(data.session_id)
        setQrImage(data.qr_image)
        setStatus('waiting')
        setMessage(data.message || `请使用 ${platformName} App 扫描二维码`)
        
        // 开始轮询检查登录状态
        startPolling(data.session_id)
      } else {
        const error = await res.json()
        setStatus('error')
        setMessage(error.detail || '获取二维码失败')
      }
    } catch (error) {
      console.error('启动登录失败:', error)
      setStatus('error')
      setMessage('网络错误，请重试')
    }
  }, [platform, platformName])

  // 轮询检查登录状态
  const startPolling = (sid: string) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }
    
    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/social-auth/qrcode/status/${sid}`)
        if (res.ok) {
          const data = await res.json()
          
          if (data.status === 'success') {
            setStatus('success')
            setMessage(data.message || '登录成功！')
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
            }
            // 2秒后关闭弹窗
            setTimeout(() => {
              onSuccess()
              onClose()
            }, 2000)
          } else if (data.status === 'timeout' || data.status === 'expired') {
            setStatus('timeout')
            setMessage(data.message || '二维码已过期')
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
            }
          } else if (data.status === 'error') {
            setStatus('error')
            setMessage(data.message || '登录失败')
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
            }
          }
        }
      } catch (error) {
        console.error('检查状态失败:', error)
      }
    }, 2000)  // 每2秒检查一次
  }

  // 刷新二维码
  const refreshQR = async () => {
    if (!sessionId) {
      startLogin()
      return
    }
    
    setStatus('loading')
    setMessage('正在刷新二维码...')
    
    try {
      const res = await fetch(`/api/social-auth/qrcode/refresh/${sessionId}`, {
        method: 'POST'
      })
      
      if (res.ok) {
        const data = await res.json()
        if (data.qr_image) {
          setQrImage(data.qr_image)
          setStatus('waiting')
          setMessage(`请使用 ${platformName} App 扫描二维码`)
          startPolling(sessionId)
        } else {
          // 会话已过期，重新开始
          startLogin()
        }
      }
    } catch (error) {
      console.error('刷新失败:', error)
      startLogin()
    }
  }

  // 组件挂载时开始登录
  useEffect(() => {
    startLogin()
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
      // 取消会话
      if (sessionId) {
        fetch(`/api/social-auth/qrcode/cancel/${sessionId}`, { method: 'POST' }).catch(() => {})
      }
    }
  }, [])

  // 状态颜色
  const statusColors = {
    loading: 'text-gray-400',
    waiting: 'text-cyber-blue',
    success: 'text-green-400',
    error: 'text-red-400',
    timeout: 'text-yellow-500'
  }

  const statusIcons = {
    loading: Loader2,
    waiting: Smartphone,
    success: Check,
    error: AlertCircle,
    timeout: RefreshCw
  }

  const StatusIcon = statusIcons[status]

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
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <QrCode className="w-5 h-5 text-cyber-purple" />
            {platformName} 扫码登录
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6 flex flex-col items-center">
          {/* 二维码区域 */}
          <div className="w-64 h-64 bg-white rounded-xl flex items-center justify-center relative overflow-hidden">
            {status === 'loading' ? (
              <Loader2 className="w-12 h-12 text-gray-400 animate-spin" />
            ) : qrImage ? (
              <>
                <img 
                  src={`data:image/png;base64,${qrImage}`} 
                  alt="扫码登录"
                  className="w-full h-full object-contain"
                />
                {status === 'timeout' && (
                  <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center">
                    <p className="text-white text-sm mb-2">二维码已过期</p>
                    <button
                      onClick={refreshQR}
                      className="px-4 py-2 bg-cyber-blue rounded-lg text-white text-sm flex items-center gap-2"
                    >
                      <RefreshCw className="w-4 h-4" />
                      点击刷新
                    </button>
                  </div>
                )}
                {status === 'success' && (
                  <div className="absolute inset-0 bg-green-500/90 flex flex-col items-center justify-center">
                    <Check className="w-16 h-16 text-white mb-2" />
                    <p className="text-white font-medium">登录成功！</p>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center p-4">
                <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-2" />
                <p className="text-gray-600 text-sm">加载失败</p>
              </div>
            )}
          </div>

          {/* 状态提示 */}
          <div className={`flex items-center gap-2 mt-6 ${statusColors[status]}`}>
            <StatusIcon className={`w-5 h-5 ${status === 'loading' ? 'animate-spin' : ''}`} />
            <span>{message}</span>
          </div>

          {/* 操作按钮 */}
          {(status === 'error' || status === 'timeout') && (
            <button
              onClick={status === 'timeout' ? refreshQR : startLogin}
              className="mt-4 px-6 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              重新获取二维码
            </button>
          )}

          {/* 使用说明 */}
          <div className="mt-6 text-gray-500 text-sm text-center space-y-1">
            <p>1. 打开 {platformName} App</p>
            <p>2. 使用扫一扫功能扫描二维码</p>
            <p>3. 在手机上确认登录</p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// 社交平台登录管理面板
function SocialPlatformPanel({ 
  platforms, 
  onCollect, 
  collecting,
  onRefresh
}: { 
  platforms: SocialPlatform[]
  onCollect: (platforms: string[]) => void
  collecting: boolean
  onRefresh: () => void
}) {
  const [showLoginModal, setShowLoginModal] = useState<{platform: string, name: string} | null>(null)

  const handleLogout = async (platform: string, name: string) => {
    if (!confirm(`确定要退出 ${name} 登录吗？`)) return
    try {
      await fetch(`/api/social-auth/logout/${platform}`, { method: 'POST' })
      onRefresh()
    } catch (error) {
      console.error('退出失败:', error)
    }
  }

  // 判断平台是否支持扫码登录
  const supportsQRLogin = (platform: string) => {
    return ['douyin', 'bilibili', 'weixin_video'].includes(platform)
  }

  const PLATFORM_ICONS_EXTENDED: Record<string, string> = {
    xiaohongshu: '📕',
    douyin: '🎵',
    bilibili: '📺',
    weixin_video: '📹',
    pexels: '📷',
    pixabay: '🖼️'
  }

  return (
    <div className="bg-dark-purple/40 rounded-xl p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-cyber-purple" />
          AI素材采集
        </h2>
        <button
          onClick={() => onCollect(['pexels', 'pixabay'])}
          disabled={collecting}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyber-purple to-pink-500 rounded-lg text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {collecting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              采集中...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              一键采集
            </>
          )}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Pexels - 已启用 */}
        <div className="bg-deep-space/50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">{PLATFORM_ICONS_EXTENDED.pexels}</span>
            <span className="text-white font-medium">Pexels</span>
          </div>
          <div className="flex items-center gap-1 text-green-400 text-sm mb-2">
            <Check className="w-4 h-4" />
            已启用
          </div>
          <p className="text-gray-500 text-xs">免版权视频素材</p>
        </div>

        {/* Pixabay - 已启用 */}
        <div className="bg-deep-space/50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">{PLATFORM_ICONS_EXTENDED.pixabay}</span>
            <span className="text-white font-medium">Pixabay</span>
          </div>
          <div className="flex items-center gap-1 text-green-400 text-sm mb-2">
            <Check className="w-4 h-4" />
            已启用
          </div>
          <p className="text-gray-500 text-xs">免版权视频素材</p>
        </div>

        {/* 社交媒体平台 */}
        {platforms.map(p => (
          <div key={p.platform} className="bg-deep-space/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{PLATFORM_ICONS_EXTENDED[p.platform] || '📱'}</span>
              <span className="text-white font-medium">{p.name}</span>
            </div>
            
            {p.is_logged_in ? (
              <>
                <div className="flex items-center gap-1 text-green-400 text-sm mb-2">
                  <Check className="w-4 h-4" />
                  <span className="truncate">{p.username || '已登录'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500 text-xs">采集 {p.total_collected} 个</span>
                  <button
                    onClick={() => handleLogout(p.platform, p.name)}
                    className="text-gray-500 hover:text-red-400 text-xs"
                  >
                    退出
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center gap-1 text-yellow-500 text-sm mb-2">
                  <AlertCircle className="w-4 h-4" />
                  未登录
                </div>
                {supportsQRLogin(p.platform) ? (
                  <button
                    onClick={() => setShowLoginModal({ platform: p.platform, name: p.name })}
                    className="flex items-center gap-1 text-cyber-blue hover:text-cyber-purple text-xs transition-colors"
                  >
                    <QrCode className="w-3 h-3" />
                    扫码登录
                  </button>
                ) : (
                  <a
                    href={
                      p.platform === 'xiaohongshu' ? 'https://www.xiaohongshu.com' : '#'
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-cyber-blue hover:underline text-xs"
                  >
                    <ExternalLink className="w-3 h-3" />
                    手动登录
                  </a>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      <p className="text-gray-500 text-xs mt-4">
        💡 提示：Pexels 和 Pixabay 已自动启用。抖音、B站、微信视频号支持<span className="text-cyber-blue">扫码登录</span>，小红书需手动获取Cookie。
      </p>

      {/* 扫码登录弹窗 */}
      <AnimatePresence>
        {showLoginModal && (
          <QRCodeLoginModal
            platform={showLoginModal.platform}
            platformName={showLoginModal.name}
            onClose={() => setShowLoginModal(null)}
            onSuccess={onRefresh}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

export default function AssetsPage() {
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [playingAsset, setPlayingAsset] = useState<Asset | null>(null)
  const [socialPlatforms, setSocialPlatforms] = useState<SocialPlatform[]>([])
  const [collecting, setCollecting] = useState(false)

  const fetchAssets = async () => {
    try {
      const params = new URLSearchParams()
      if (selectedCategory !== 'all') {
        params.append('type', selectedCategory)
      }
      
      const res = await fetch(`/api/assets?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setAssets(data.items || [])
      }
    } catch (error) {
      console.error('获取素材列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchSocialPlatforms = async () => {
    try {
      const res = await fetch('/api/social-auth/platforms')
      if (res.ok) {
        const data = await res.json()
        setSocialPlatforms(data.platforms || [])
      }
    } catch (error) {
      console.error('获取平台状态失败:', error)
    }
  }

  const handleAICollect = async (platforms: string[]) => {
    setCollecting(true)
    try {
      // 从Pexels和Pixabay采集免版权素材
      const res = await fetch('/api/assets/collect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keywords: ['logistics warehouse', 'container shipping', 'cargo transport', 'supply chain'],
          platforms: ['pexels', 'pixabay']
        })
      })

      if (res.ok) {
        const data = await res.json()
        alert(`采集完成！共发现 ${data.found || 0} 个素材`)
        fetchAssets()
      } else {
        alert('采集失败，请重试')
      }
    } catch (error) {
      console.error('采集失败:', error)
      alert('采集失败，请重试')
    } finally {
      setCollecting(false)
    }
  }

  useEffect(() => {
    setLoading(true)
    fetchAssets()
    fetchSocialPlatforms()
  }, [selectedCategory])

  const handleDownload = (asset: Asset) => {
    if (!asset.file_url) {
      alert('文件不存在')
      return
    }
    const a = document.createElement('a')
    a.href = asset.file_url
    a.download = asset.name
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const handleDelete = async (assetId: string) => {
    if (!confirm('确定要删除这个素材吗？')) return
    
    try {
      const res = await fetch(`/api/assets/${assetId}`, { method: 'DELETE' })
      if (res.ok) {
        setAssets(prev => prev.filter(a => a.id !== assetId))
      } else {
        alert('删除失败，请重试')
      }
    } catch (error) {
      console.error('删除失败:', error)
      alert('删除失败，请检查网络')
    }
  }

  const filteredAssets = assets

  const typeIcons = {
    video: Video,
    audio: Music,
    image: Image
  }

  const typeColors = {
    video: 'text-blue-400 bg-blue-400/10',
    audio: 'text-green-400 bg-green-400/10',
    image: 'text-purple-400 bg-purple-400/10'
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <FolderOpen className="w-7 h-7 text-cyber-blue" />
            素材库管理
          </h1>
          <p className="text-gray-400 mt-1">管理视频素材、背景音乐和图片资源</p>
        </div>
        <button 
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity"
        >
          <Upload className="w-4 h-4" />
          上传素材
        </button>
      </div>

      {/* 社交平台管理面板 */}
      <SocialPlatformPanel
        platforms={socialPlatforms}
        onCollect={handleAICollect}
        collecting={collecting}
        onRefresh={fetchSocialPlatforms}
      />

      {/* 分类和视图切换 */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                selectedCategory === cat.id
                  ? 'bg-cyber-blue text-white'
                  : 'bg-dark-purple/40 text-gray-400 hover:text-white'
              }`}
            >
              <cat.icon className="w-4 h-4" />
              {cat.name}
            </button>
          ))}
        </div>
        <div className="flex bg-dark-purple/40 rounded-lg p-1">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 rounded ${viewMode === 'grid' ? 'bg-white/10 text-white' : 'text-gray-500'}`}
          >
            <Grid className="w-5 h-5" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 rounded ${viewMode === 'list' ? 'bg-white/10 text-white' : 'text-gray-500'}`}
          >
            <List className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 素材列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-cyber-blue" />
        </div>
      ) : filteredAssets.length === 0 ? (
        <div className="bg-dark-purple/40 rounded-xl p-12 text-center">
          <FolderOpen className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg mb-4">暂无素材</p>
          <button
            onClick={() => setShowUploadModal(true)}
            className="text-cyber-blue hover:underline"
          >
            点击上传第一个素材
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredAssets.map(asset => {
            const TypeIcon = typeIcons[asset.type]
            return (
              <motion.div
                key={asset.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-dark-purple/40 rounded-xl overflow-hidden group cursor-pointer hover:ring-1 hover:ring-cyber-blue/50 transition-all"
              >
                <div className="aspect-video bg-deep-space/50 relative flex items-center justify-center">
                  {asset.thumbnail_url ? (
                    <img src={asset.thumbnail_url} alt={asset.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className={`p-4 rounded-full ${typeColors[asset.type]}`}>
                      <TypeIcon className="w-8 h-8" />
                    </div>
                  )}
                  {asset.duration && (
                    <span className="absolute bottom-2 right-2 px-2 py-0.5 bg-black/70 text-white text-xs rounded">
                      {formatDuration(asset.duration)}
                    </span>
                  )}
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <button 
                      onClick={() => setPlayingAsset(asset)}
                      className="p-2 bg-white/20 hover:bg-white/30 rounded-full text-white"
                    >
                      <Play className="w-5 h-5" />
                    </button>
                    <button 
                      onClick={() => handleDownload(asset)}
                      className="p-2 bg-white/20 hover:bg-white/30 rounded-full text-white"
                    >
                      <Download className="w-5 h-5" />
                    </button>
                    <button 
                      onClick={() => handleDelete(asset.id)}
                      className="p-2 bg-white/20 hover:bg-red-500/50 rounded-full text-white"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                <div className="p-3">
                  <h3 className="text-white text-sm font-medium truncate">{asset.name}</h3>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-gray-500 text-xs">{formatFileSize(asset.file_size)}</span>
                    <span className="text-gray-500 text-xs">使用 {asset.usage_count} 次</span>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      ) : (
        <div className="bg-dark-purple/40 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-deep-space/50">
              <tr>
                <th className="px-4 py-3 text-left text-gray-400 text-sm font-medium">名称</th>
                <th className="px-4 py-3 text-left text-gray-400 text-sm font-medium">类型</th>
                <th className="px-4 py-3 text-left text-gray-400 text-sm font-medium">时长</th>
                <th className="px-4 py-3 text-left text-gray-400 text-sm font-medium">大小</th>
                <th className="px-4 py-3 text-left text-gray-400 text-sm font-medium">使用次数</th>
                <th className="px-4 py-3 text-right text-gray-400 text-sm font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {filteredAssets.map(asset => {
                const TypeIcon = typeIcons[asset.type]
                return (
                  <tr key={asset.id} className="hover:bg-white/5">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${typeColors[asset.type]}`}>
                          <TypeIcon className="w-4 h-4" />
                        </div>
                        <span className="text-white">{asset.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">{asset.category}</td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {asset.duration ? formatDuration(asset.duration) : '-'}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">{formatFileSize(asset.file_size)}</td>
                    <td className="px-4 py-3 text-gray-400 text-sm">{asset.usage_count}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button 
                          onClick={() => setPlayingAsset(asset)}
                          className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/10"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => handleDownload(asset)}
                          className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/10"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => handleDelete(asset.id)}
                          className="p-2 text-gray-400 hover:text-red-400 rounded-lg hover:bg-white/10"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 上传弹窗 */}
      <AnimatePresence>
        {showUploadModal && (
          <UploadModal
            onClose={() => setShowUploadModal(false)}
            onUpload={fetchAssets}
          />
        )}
      </AnimatePresence>

      {/* 播放弹窗 */}
      <AnimatePresence>
        {playingAsset && (
          <PlayModal
            asset={playingAsset}
            onClose={() => setPlayingAsset(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
