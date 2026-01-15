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

// 扫码登录弹窗 - 跳转官方页面方案
// 平台特定配置
const PLATFORM_LOGIN_CONFIG: Record<string, {
  loginPageName: string
  scanMethod: string
  cookieDomain: string
  keyCookies: string[]
  cookieHint: string
}> = {
  douyin: {
    loginPageName: '抖音创作者中心',
    scanMethod: '打开抖音App → 点击左上角扫一扫',
    cookieDomain: '.douyin.com 或 creator.douyin.com',
    keyCookies: ['sessionid', 'passport_csrf_token', 'sid_guard'],
    cookieHint: '选择 https://creator.douyin.com 下的Cookies'
  },
  bilibili: {
    loginPageName: 'B站主页',
    scanMethod: '打开B站App → 扫一扫',
    cookieDomain: '.bilibili.com',
    keyCookies: ['SESSDATA', 'bili_jct', 'DedeUserID'],
    cookieHint: '选择 .bilibili.com 下的Cookies'
  },
  weixin_video: {
    loginPageName: '微信视频号',
    scanMethod: '打开微信 → 扫一扫',
    cookieDomain: '.qq.com 或 channels.weixin.qq.com',
    keyCookies: ['uin', 'skey', 'wxuin'],
    cookieHint: '选择 channels.weixin.qq.com 下的Cookies'
  },
  xiaohongshu: {
    loginPageName: '小红书创作者中心',
    scanMethod: '打开小红书App → 扫一扫',
    cookieDomain: '.xiaohongshu.com',
    keyCookies: ['web_session', 'a1', 'webId'],
    cookieHint: '选择 .xiaohongshu.com 下的Cookies'
  }
}

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
  const [step, setStep] = useState<'guide' | 'paste' | 'verifying' | 'success' | 'error'>('guide')
  const [loginUrl, setLoginUrl] = useState('')
  const [cookieStr, setCookieStr] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  
  // 获取平台配置
  const config = PLATFORM_LOGIN_CONFIG[platform] || {
    loginPageName: `${platformName}官网`,
    scanMethod: `打开${platformName}App扫码`,
    cookieDomain: '当前网站',
    keyCookies: ['session'],
    cookieHint: '选择当前网站的Cookies'
  }

  // 打开登录页面 - 点击时获取URL并打开
  const openLoginPage = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/social-auth/qrcode/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform })
      })
      if (res.ok) {
        const data = await res.json()
        const url = data.login_url
        if (url) {
          setLoginUrl(url)
          // 使用 window.open 打开新窗口
          const newWindow = window.open(url, '_blank')
          if (!newWindow || newWindow.closed) {
            // 如果弹窗被阻止，复制链接到剪贴板
            try {
              await navigator.clipboard.writeText(url)
              setMessage('链接已复制！请手动在浏览器中粘贴打开')
            } catch {
              setMessage('请手动复制下方链接打开')
            }
          }
        }
      } else {
        setMessage('获取登录链接失败，请重试')
      }
    } catch (error) {
      console.error('获取登录URL失败:', error)
      setMessage('网络错误，请重试')
    } finally {
      setLoading(false)
    }
  }

  // 验证Cookie
  const verifyCookies = async () => {
    if (!cookieStr.trim()) {
      setMessage('请粘贴Cookie')
      return
    }

    setStep('verifying')
    setMessage('正在验证...')

    try {
      const res = await fetch('/api/social-auth/qrcode/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          cookies_str: cookieStr
        })
      })

      const data = await res.json()

      if (data.status === 'success') {
        setStep('success')
        setMessage(data.message || '登录成功！')
        setTimeout(() => {
          onSuccess()
          onClose()
        }, 1500)
      } else {
        setStep('error')
        setMessage(data.message || '验证失败')
      }
    } catch (error) {
      console.error('验证失败:', error)
      setStep('error')
      setMessage('网络错误，请重试')
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
        className="bg-dark-purple/90 backdrop-blur-xl border border-white/10 rounded-xl w-full max-w-lg mx-4"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <QrCode className="w-5 h-5 text-cyber-purple" />
            {platformName} 登录
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6">
          {/* 步骤1: 引导 */}
          {step === 'guide' && (
            <div className="space-y-6">
              <div className="bg-deep-space/50 rounded-xl p-6">
                <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                  <span className="w-6 h-6 bg-cyber-blue rounded-full flex items-center justify-center text-sm">1</span>
                  打开 {config.loginPageName}
                </h3>
                <button
                  onClick={openLoginPage}
                  disabled={loading}
                  className="w-full py-3 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      正在打开...
                    </>
                  ) : (
                    <>
                      <ExternalLink className="w-5 h-5" />
                      打开 {config.loginPageName}
                    </>
                  )}
                </button>
                <p className="text-gray-500 text-sm mt-3 text-center">
                  将在新窗口中打开 <span className="text-cyber-blue">{config.loginPageName}</span>
                </p>
                {loginUrl && (
                  <div className="mt-4 p-3 bg-cyber-blue/10 rounded-lg">
                    <p className="text-xs text-gray-400 mb-2">如果弹窗被阻止，请手动打开：</p>
                    <a 
                      href={loginUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-cyber-blue hover:underline break-all"
                    >
                      {loginUrl}
                    </a>
                  </div>
                )}
                {message && (
                  <p className="text-xs text-yellow-400 mt-2 text-center">{message}</p>
                )}
              </div>

              <div className="bg-deep-space/50 rounded-xl p-6">
                <h3 className="text-white font-medium mb-3 flex items-center gap-2">
                  <span className="w-6 h-6 bg-gray-600 rounded-full flex items-center justify-center text-sm">2</span>
                  扫码登录
                </h3>
                <p className="text-gray-400 text-sm">
                  <span className="text-cyber-blue">{config.scanMethod}</span>
                  <br />扫描页面上的二维码完成登录
                </p>
              </div>

              <div className="bg-deep-space/50 rounded-xl p-6">
                <h3 className="text-white font-medium mb-3 flex items-center gap-2">
                  <span className="w-6 h-6 bg-gray-600 rounded-full flex items-center justify-center text-sm">3</span>
                  复制 Cookie 并粘贴
                </h3>
                <div className="text-gray-400 text-sm mb-3 space-y-2">
                  <p>登录成功后：</p>
                  <ol className="list-decimal list-inside space-y-1 text-xs">
                    <li>按 <span className="text-white bg-gray-700 px-1 rounded">F12</span> 打开开发者工具</li>
                    <li>点击 <span className="text-white">Application</span>（应用）标签</li>
                    <li>左侧展开 <span className="text-white">Cookies</span> → <span className="text-cyber-blue">{config.cookieHint}</span></li>
                    <li>右侧表格 <span className="text-white">Ctrl+A</span> 全选 → <span className="text-white">Ctrl+C</span> 复制</li>
                  </ol>
                  <p className="text-xs text-yellow-400 mt-2">
                    💡 关键Cookie: <span className="text-white">{config.keyCookies.join(', ')}</span>
                  </p>
                </div>
                <button
                  onClick={() => setStep('paste')}
                  className="w-full py-2.5 border border-cyber-blue text-cyber-blue rounded-lg hover:bg-cyber-blue/10 transition-colors"
                >
                  我已完成登录，去粘贴Cookie
                </button>
              </div>
            </div>
          )}

          {/* 步骤2: 粘贴Cookie */}
          {step === 'paste' && (
            <div className="space-y-4">
              <div>
                <label className="block text-gray-300 text-sm mb-2">
                  粘贴从浏览器复制的Cookie
                </label>
                <textarea
                  value={cookieStr}
                  onChange={e => setCookieStr(e.target.value)}
                  placeholder={`从 ${config.loginPageName} 页面的开发者工具中复制Cookie粘贴到这里...\n\n支持格式：\n1. name=value; name2=value2\n2. 从开发者工具直接复制的表格格式`}
                  className="w-full h-48 px-4 py-3 bg-deep-space/50 border border-gray-700 rounded-lg text-white text-sm focus:border-cyber-blue focus:outline-none resize-none font-mono"
                />
              </div>

              {message && (
                <p className="text-red-400 text-sm">{message}</p>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => setStep('guide')}
                  className="flex-1 py-2.5 border border-gray-600 text-gray-400 rounded-lg hover:text-white hover:border-gray-500 transition-colors"
                >
                  返回
                </button>
                <button
                  onClick={verifyCookies}
                  className="flex-1 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity"
                >
                  验证并保存
                </button>
              </div>

              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                <p className="text-yellow-400 text-sm">
                  💡 {platformName} Cookie 获取指南：
                </p>
                <ol className="text-yellow-400/80 text-xs mt-2 space-y-1 list-decimal list-inside">
                  <li>在 <span className="text-white">{config.loginPageName}</span> 登录成功后</li>
                  <li>按 <span className="text-white bg-gray-700 px-1 rounded">F12</span> 打开开发者工具</li>
                  <li>点击 <span className="text-white">Application</span>（应用）标签</li>
                  <li>左侧 Cookies → 选择 <span className="text-cyan-400">{config.cookieDomain}</span></li>
                  <li>右侧表格 <span className="text-white">Ctrl+A</span> 全选 → <span className="text-white">Ctrl+C</span> 复制</li>
                </ol>
                <p className="text-xs text-gray-400 mt-3">
                  🔑 确保包含: <span className="text-green-400">{config.keyCookies.join(', ')}</span>
                </p>
              </div>
            </div>
          )}

          {/* 验证中 */}
          {step === 'verifying' && (
            <div className="flex flex-col items-center py-12">
              <Loader2 className="w-12 h-12 text-cyber-blue animate-spin mb-4" />
              <p className="text-gray-400">{message}</p>
            </div>
          )}

          {/* 成功 */}
          {step === 'success' && (
            <div className="flex flex-col items-center py-12">
              <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mb-4">
                <Check className="w-10 h-10 text-white" />
              </div>
              <p className="text-green-400 font-medium text-lg">{message}</p>
            </div>
          )}

          {/* 失败 */}
          {step === 'error' && (
            <div className="flex flex-col items-center py-12">
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mb-4">
                <AlertCircle className="w-10 h-10 text-red-400" />
              </div>
              <p className="text-red-400 mb-4">{message}</p>
              <button
                onClick={() => setStep('paste')}
                className="px-6 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity"
              >
                重试
              </button>
            </div>
          )}
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
