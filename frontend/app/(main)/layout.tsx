'use client'

import { useState, useEffect } from 'react'
import Sidebar, { MobileHeader } from '@/components/Sidebar'

export default function MainLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [isMobile, setIsMobile] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  // 检测屏幕尺寸
  useEffect(() => {
    const checkScreenSize = () => {
      const mobile = window.innerWidth < 1024 // lg breakpoint
      setIsMobile(mobile)
      // 移动端默认关闭侧边栏，桌面端默认打开
      if (mobile) {
        setSidebarOpen(false)
      } else {
        // 恢复桌面端侧边栏状态
        const savedState = localStorage.getItem('sidebarOpen')
        setSidebarOpen(savedState !== 'false')
      }
    }
    
    checkScreenSize()
    window.addEventListener('resize', checkScreenSize)
    return () => window.removeEventListener('resize', checkScreenSize)
  }, [])

  // 保存侧边栏状态到本地存储（仅桌面端）
  useEffect(() => {
    if (!isMobile) {
      localStorage.setItem('sidebarOpen', String(sidebarOpen))
    }
  }, [sidebarOpen, isMobile])

  // 获取未读通知数量（用于移动端顶栏）
  useEffect(() => {
    const fetchUnreadCount = async () => {
      try {
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
    const interval = setInterval(fetchUnreadCount, 60000)
    return () => clearInterval(interval)
  }, [])

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  return (
    <div className="min-h-screen">
      {/* 移动端顶部导航 */}
      <MobileHeader onMenuClick={toggleSidebar} unreadCount={unreadCount} />
      
      {/* 侧边栏 */}
      <Sidebar isOpen={sidebarOpen} onToggle={toggleSidebar} isMobile={isMobile} />
      
      {/* 主内容区域 - 响应式边距 */}
      <main 
        className={`
          min-h-screen
          transition-all duration-300 ease-in-out
          pt-16 lg:pt-0
          ${sidebarOpen ? 'lg:ml-64' : 'lg:ml-16'}
        `}
      >
        <div className="p-4 md:p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
