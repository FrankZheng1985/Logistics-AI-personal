'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState, useEffect } from 'react'
import { 
  LayoutDashboard, 
  Users, 
  MessageSquare, 
  Video, 
  Bot,
  Settings,
  Bell,
  Target,
  BookOpen,
  ClipboardCheck,
  Activity,
  FolderOpen,
  Mail,
  MessageCircle,
  Database,
  Smartphone,
  ShoppingCart
} from 'lucide-react'

const menuItems = [
  { href: '/dashboard', label: '控制台', icon: LayoutDashboard },
  { href: '/customers', label: '客户管理', icon: Users },
  { href: '/leads', label: '线索狩猎', icon: Target },
  { href: '/products', label: '产品趋势', icon: ShoppingCart },
  { href: '/content', label: '内容工作台', icon: Smartphone },
  { href: '/conversations', label: '对话记录', icon: MessageSquare },
  { href: '/videos', label: '视频中心', icon: Video },
  { href: '/team', label: 'AI团队', icon: Bot },
]

const managementItems = [
  { href: '/knowledge', label: '知识库', icon: BookOpen },
  { href: '/standards', label: '工作标准', icon: ClipboardCheck },
  { href: '/monitoring', label: '系统监控', icon: Activity },
  { href: '/assets', label: '素材库', icon: FolderOpen },
  { href: '/marketing', label: '营销序列', icon: Mail },
  { href: '/wechat-groups', label: '微信群监控', icon: MessageCircle },
  { href: '/settings/erp', label: 'ERP对接', icon: Database },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [unreadCount, setUnreadCount] = useState(0)
  
  // 获取未读通知数量
  useEffect(() => {
    const fetchUnreadCount = async () => {
      try {
        // 使用相对路径，通过nginx代理访问API
        const response = await fetch('/api/notifications?limit=1')
        if (response.ok) {
          const data = await response.json()
          setUnreadCount(data.unread_count || 0)
        }
      } catch (error) {
        console.error('获取通知数量失败:', error)
      }
    }
    
    fetchUnreadCount()
    // 每60秒刷新一次未读数量
    const interval = setInterval(fetchUnreadCount, 60000)
    return () => clearInterval(interval)
  }, [])
  
  return (
    <aside className="w-64 h-screen fixed left-0 top-0 bg-dark-purple/50 border-r border-white/10 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <h1 className="text-xl font-tech font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
          AI获客中心
        </h1>
        <p className="text-gray-500 text-sm mt-1">物流智能体</p>
      </div>
      
      {/* 菜单 */}
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {/* 主要功能 */}
        <p className="px-4 py-2 text-xs text-gray-500 uppercase tracking-wider">主要功能</p>
        {menuItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all ${
                isActive 
                  ? 'bg-cyber-blue/20 text-cyber-blue border border-cyber-blue/30' 
                  : 'text-gray-400 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-sm">{item.label}</span>
            </Link>
          )
        })}
        
        {/* 系统管理 */}
        <p className="px-4 py-2 pt-4 text-xs text-gray-500 uppercase tracking-wider">系统管理</p>
        {managementItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all ${
                isActive 
                  ? 'bg-cyber-blue/20 text-cyber-blue border border-cyber-blue/30' 
                  : 'text-gray-400 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-sm">{item.label}</span>
            </Link>
          )
        })}
      </nav>
      
      {/* 底部 */}
      <div className="p-4 border-t border-white/10 space-y-2">
        <Link
          href="/notifications"
          className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-400 hover:bg-white/5 hover:text-white transition-colors"
        >
          <Bell className="w-5 h-5" />
          <span>通知</span>
          {unreadCount > 0 && (
            <span className="ml-auto px-2 py-0.5 bg-alert-red/20 text-alert-red text-xs rounded-full">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </Link>
        <Link
          href="/settings"
          className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-400 hover:bg-white/5 hover:text-white transition-colors"
        >
          <Settings className="w-5 h-5" />
          <span>设置</span>
        </Link>
      </div>
    </aside>
  )
}
