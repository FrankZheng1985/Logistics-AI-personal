'use client'

import { useState } from 'react'
import { FolderOpen, Upload, Video, Music, Image, Grid, List, Play, Download } from 'lucide-react'

interface Asset {
  id: string
  name: string
  type: 'video' | 'audio' | 'image'
  category: string
  duration?: number
  thumbnail?: string
  file_size: number
  usage_count: number
}

const categories = [
  { id: 'all', name: '全部', icon: FolderOpen },
  { id: 'video_clip', name: '视频素材', icon: Video },
  { id: 'bgm', name: '背景音乐', icon: Music },
  { id: 'image', name: '图片素材', icon: Image }
]

const mockAssets: Asset[] = [
  { id: '1', name: '港口航拍01', type: 'video', category: 'port', duration: 15, file_size: 52428800, usage_count: 45 },
  { id: '2', name: '仓库内景01', type: 'video', category: 'warehouse', duration: 12, file_size: 41943040, usage_count: 38 },
  { id: '3', name: '商务专业BGM', type: 'audio', category: 'bgm_corporate', duration: 180, file_size: 5242880, usage_count: 124 },
  { id: '4', name: '活力动感BGM', type: 'audio', category: 'bgm_upbeat', duration: 150, file_size: 4718592, usage_count: 89 },
  { id: '5', name: '货车运输01', type: 'video', category: 'truck', duration: 10, file_size: 31457280, usage_count: 56 },
  { id: '6', name: '飞机装货01', type: 'video', category: 'airplane', duration: 8, file_size: 25165824, usage_count: 34 }
]

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

export default function AssetsPage() {
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [assets] = useState<Asset[]>(mockAssets)

  const filteredAssets = assets.filter(
    a => selectedCategory === 'all' || a.type === selectedCategory.replace('_clip', '')
  )

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
        <button className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity">
          <Upload className="w-4 h-4" />
          上传素材
        </button>
      </div>

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
                  : 'bg-dark-card text-gray-400 hover:text-white'
              }`}
            >
              <cat.icon className="w-4 h-4" />
              {cat.name}
            </button>
          ))}
        </div>
        <div className="flex bg-dark-card rounded-lg p-1">
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
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredAssets.map(asset => {
            const TypeIcon = typeIcons[asset.type]
            return (
              <div
                key={asset.id}
                className="bg-dark-card rounded-xl overflow-hidden group cursor-pointer hover:ring-1 hover:ring-cyber-blue/50 transition-all"
              >
                <div className="aspect-video bg-dark-bg relative flex items-center justify-center">
                  <div className={`p-4 rounded-full ${typeColors[asset.type]}`}>
                    <TypeIcon className="w-8 h-8" />
                  </div>
                  {asset.duration && (
                    <span className="absolute bottom-2 right-2 px-2 py-0.5 bg-black/70 text-white text-xs rounded">
                      {formatDuration(asset.duration)}
                    </span>
                  )}
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <button className="p-2 bg-white/20 hover:bg-white/30 rounded-full text-white">
                      <Play className="w-5 h-5" />
                    </button>
                    <button className="p-2 bg-white/20 hover:bg-white/30 rounded-full text-white">
                      <Download className="w-5 h-5" />
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
              </div>
            )
          })}
        </div>
      ) : (
        <div className="bg-dark-card rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-dark-bg">
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
                      <button className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/10">
                        <Download className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
