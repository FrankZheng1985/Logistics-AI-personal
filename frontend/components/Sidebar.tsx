'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  LayoutDashboard, 
  Users, 
  MessageSquare, 
  Video, 
  Bot,
  Settings,
  Bell,
  Target
} from 'lucide-react'

const menuItems = [
  { href: '/dashboard', label: '控制台', icon: LayoutDashboard },
  { href: '/customers', label: '客户管理', icon: Users },
  { href: '/leads', label: '线索狩猎', icon: Target },
  { href: '/conversations', label: '对话记录', icon: MessageSquare },
  { href: '/videos', label: '视频中心', icon: Video },
  { href: '/team', label: 'AI团队', icon: Bot },
]

export default function Sidebar() {
  const pathname = usePathname()
  
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
      <nav className="flex-1 p-4 space-y-2">
        {menuItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive 
                  ? 'bg-cyber-blue/20 text-cyber-blue border border-cyber-blue/30' 
                  : 'text-gray-400 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
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
          <span className="ml-auto px-2 py-0.5 bg-alert-red/20 text-alert-red text-xs rounded-full">3</span>
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
