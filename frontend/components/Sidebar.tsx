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
  ShoppingCart,
  CalendarCheck,
  Menu,
  X,
  ChevronLeft,
  Cpu
} from 'lucide-react'

const menuItems = [
  { href: '/dashboard', label: '控制台', icon: LayoutDashboard },
  { href: '/customers', label: '客户管理', icon: Users },
  { href: '/leads', label: '线索狩猎', icon: Target },
  { href: '/products', label: '产品趋势', icon: ShoppingCart },
  { href: '/content', label: '内容工作台', icon: Smartphone },
  { href: '/assistant-work', label: '小助工作台', icon: CalendarCheck },
  { href: '/conversations', label: '对话记录', icon: MessageSquare },
  { href: '/videos', label: '视频中心', icon: Video },
  { href: '/team', label: 'AI团队', icon: Bot },
]

const managementItems = [
  { href: '/knowledge', label: '知识库', icon: BookOpen },
  { href: '/standards', label: '工作标准', icon: ClipboardCheck },
  { href: '/monitoring', label: '系统监控', icon: Activity },
  { href: '/ai-usage', label: 'AI用量监控', icon: Cpu },
  { href: '/assets', label: '素材库', icon: FolderOpen },
  { href: '/marketing', label: '营销序列', icon: Mail },
  { href: '/wechat-groups', label: '微信群监控', icon: MessageCircle },
  { href: '/settings/erp', label: 'ERP对接', icon: Database },
]

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
  isMobile: boolean
}

export default function Sidebar({ isOpen, onToggle, isMobile }: SidebarProps) {
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

  // 在移动端点击菜单项后关闭侧边栏
  const handleMenuClick = () => {
    if (isMobile && isOpen) {
      onToggle()
    }
  }
  
  return (
    <>
      {/* 移动端遮罩层 */}
      {isMobile && isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onToggle}
        />
      )}
      
      {/* 侧边栏 */}
      <aside 
        className={`
          fixed left-0 top-0 h-screen z-50
          bg-dark-purple/95 backdrop-blur-xl border-r border-white/10
          flex flex-col
          transition-all duration-300 ease-in-out
          ${isOpen ? 'w-64' : 'w-0 lg:w-16'}
          ${isMobile && !isOpen ? '-translate-x-full' : 'translate-x-0'}
        `}
      >
        {/* Logo */}
        <div className={`p-4 lg:p-6 border-b border-white/10 ${!isOpen && !isMobile ? 'flex justify-center' : ''}`}>
          {isOpen ? (
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-tech font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
                  AI获客中心
                </h1>
                <p className="text-gray-500 text-sm mt-1">物流智能体</p>
              </div>
              {/* 移动端关闭按钮 */}
              {isMobile && (
                <button 
                  onClick={onToggle}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors lg:hidden"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              )}
            </div>
          ) : (
            <div className="hidden lg:flex flex-col items-center">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-r from-cyber-blue to-neon-purple flex items-center justify-center font-bold text-sm">
                AI
              </div>
            </div>
          )}
        </div>
        
        {/* 菜单 */}
        <nav className={`flex-1 p-2 lg:p-4 space-y-1 lg:space-y-2 overflow-y-auto ${!isOpen && 'lg:px-2'}`}>
          {/* 主要功能 */}
          {isOpen && (
            <p className="px-4 py-2 text-xs text-gray-500 uppercase tracking-wider">主要功能</p>
          )}
          {menuItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            const Icon = item.icon
            
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={handleMenuClick}
                title={!isOpen ? item.label : undefined}
                className={`
                  flex items-center gap-3 px-3 lg:px-4 py-2.5 rounded-lg transition-all
                  ${!isOpen && 'lg:justify-center lg:px-2'}
                  ${isActive 
                    ? 'bg-cyber-blue/20 text-cyber-blue border border-cyber-blue/30' 
                    : 'text-gray-400 hover:bg-white/5 hover:text-white'
                  }
                `}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {isOpen && <span className="text-sm whitespace-nowrap">{item.label}</span>}
              </Link>
            )
          })}
          
          {/* 系统管理 */}
          {isOpen && (
            <p className="px-4 py-2 pt-4 text-xs text-gray-500 uppercase tracking-wider">系统管理</p>
          )}
          {!isOpen && <div className="hidden lg:block border-t border-white/10 my-2" />}
          {managementItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            const Icon = item.icon
            
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={handleMenuClick}
                title={!isOpen ? item.label : undefined}
                className={`
                  flex items-center gap-3 px-3 lg:px-4 py-2.5 rounded-lg transition-all
                  ${!isOpen && 'lg:justify-center lg:px-2'}
                  ${isActive 
                    ? 'bg-cyber-blue/20 text-cyber-blue border border-cyber-blue/30' 
                    : 'text-gray-400 hover:bg-white/5 hover:text-white'
                  }
                `}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {isOpen && <span className="text-sm whitespace-nowrap">{item.label}</span>}
              </Link>
            )
          })}
        </nav>
        
        {/* 底部 */}
        <div className={`p-2 lg:p-4 border-t border-white/10 space-y-1 lg:space-y-2 ${!isOpen && 'lg:px-2'}`}>
          <Link
            href="/notifications"
            onClick={handleMenuClick}
            title={!isOpen ? '通知' : undefined}
            className={`
              flex items-center gap-3 px-3 lg:px-4 py-3 rounded-lg 
              text-gray-400 hover:bg-white/5 hover:text-white transition-colors
              ${!isOpen && 'lg:justify-center lg:px-2'}
            `}
          >
            <div className="relative flex-shrink-0">
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-alert-red text-white text-[10px] rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </div>
            {isOpen && (
              <>
                <span>通知</span>
                {unreadCount > 0 && (
                  <span className="ml-auto px-2 py-0.5 bg-alert-red/20 text-alert-red text-xs rounded-full">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </>
            )}
          </Link>
          <Link
            href="/settings"
            onClick={handleMenuClick}
            title={!isOpen ? '设置' : undefined}
            className={`
              flex items-center gap-3 px-3 lg:px-4 py-3 rounded-lg 
              text-gray-400 hover:bg-white/5 hover:text-white transition-colors
              ${!isOpen && 'lg:justify-center lg:px-2'}
            `}
          >
            <Settings className="w-5 h-5 flex-shrink-0" />
            {isOpen && <span>设置</span>}
          </Link>
          
          {/* 桌面端折叠按钮 */}
          {!isMobile && (
            <button
              onClick={onToggle}
              className={`
                hidden lg:flex items-center gap-3 w-full px-3 lg:px-4 py-3 rounded-lg 
                text-gray-400 hover:bg-white/5 hover:text-white transition-colors
                ${!isOpen && 'lg:justify-center lg:px-2'}
              `}
            >
              <ChevronLeft className={`w-5 h-5 flex-shrink-0 transition-transform ${!isOpen && 'rotate-180'}`} />
              {isOpen && <span>收起菜单</span>}
            </button>
          )}
        </div>
      </aside>
    </>
  )
}

// 移动端顶部导航栏组件
export function MobileHeader({ onMenuClick, unreadCount }: { onMenuClick: () => void; unreadCount?: number }) {
  return (
    <header className="fixed top-0 left-0 right-0 z-30 lg:hidden bg-dark-purple/95 backdrop-blur-xl border-b border-white/10">
      <div className="flex items-center justify-between px-4 py-3">
        <button 
          onClick={onMenuClick}
          className="p-2 hover:bg-white/10 rounded-lg transition-colors"
        >
          <Menu className="w-6 h-6 text-gray-400" />
        </button>
        
        <h1 className="text-lg font-tech font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
          AI获客中心
        </h1>
        
        <Link href="/notifications" className="p-2 hover:bg-white/10 rounded-lg transition-colors relative">
          <Bell className="w-5 h-5 text-gray-400" />
          {unreadCount && unreadCount > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 bg-alert-red text-white text-[10px] rounded-full flex items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Link>
      </div>
    </header>
  )
}
