'use client'

import WebChat from '@/components/WebChat'

export default function ChatWidgetPage() {
  return (
    <div className="min-h-screen bg-transparent">
      <WebChat 
        position="bottom-right"
        primaryColor="#00D4FF"
        title="小销 · 物流顾问"
        subtitle="欧洲清关·运输·派送 一站式服务"
      />
    </div>
  )
}
