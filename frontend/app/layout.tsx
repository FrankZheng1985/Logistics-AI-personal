import type { Metadata } from 'next'
import { Orbitron, JetBrains_Mono, Noto_Sans_SC } from 'next/font/google'
import './globals.css'

const orbitron = Orbitron({ 
  subsets: ['latin'],
  variable: '--font-tech',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({ 
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

const notoSansSC = Noto_Sans_SC({ 
  subsets: ['latin'],
  variable: '--font-chinese',
  weight: ['400', '500', '700'],
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'AI获客控制中心 | 物流智能体',
  description: '物流获客AI员工团队管理系统',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className={`${orbitron.variable} ${jetbrainsMono.variable} ${notoSansSC.variable}`}>
      <body className="bg-deep-space text-white font-chinese antialiased">
        {children}
      </body>
    </html>
  )
}
