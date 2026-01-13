'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="text-center"
      >
        <motion.h1 
          className="text-5xl md:text-7xl font-tech font-bold mb-6"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
            AI获客控制中心
          </span>
        </motion.h1>
        
        <motion.p 
          className="text-xl text-gray-400 mb-12"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.5 }}
        >
          物流行业智能获客 · 6名AI员工为您服务
        </motion.p>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.5 }}
        >
          <Link 
            href="/dashboard"
            className="btn-cyber inline-block text-lg"
          >
            进入控制台
          </Link>
        </motion.div>
        
        {/* AI员工头像预览 */}
        <motion.div 
          className="mt-16 flex justify-center gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.5 }}
        >
          {['小调', '小视', '小文', '小销', '小跟', '小析'].map((name, i) => (
            <motion.div
              key={name}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 1 + i * 0.1, duration: 0.3 }}
              className="w-14 h-14 rounded-full glass-card flex items-center justify-center text-sm font-medium border-cyber-blue/30 hover:border-cyber-blue/60 transition-colors cursor-pointer"
            >
              {name}
            </motion.div>
          ))}
        </motion.div>
      </motion.div>
    </main>
  )
}
