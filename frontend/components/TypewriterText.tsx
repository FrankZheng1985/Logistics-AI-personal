'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface TypewriterTextProps {
  content: string
  isStreaming?: boolean
  className?: string
  cursorClassName?: string
  showCursor?: boolean
}

/**
 * 打字机效果文本组件
 * 用于显示AI实时生成的内容
 */
export function TypewriterText({
  content,
  isStreaming = false,
  className = '',
  cursorClassName = '',
  showCursor = true
}: TypewriterTextProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  
  // 自动滚动到底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [content])
  
  return (
    <div 
      ref={containerRef}
      className={`font-mono whitespace-pre-wrap overflow-auto ${className}`}
    >
      <span>{content}</span>
      {showCursor && isStreaming && (
        <motion.span
          className={`inline-block w-2 h-4 bg-cyan-400 ml-0.5 ${cursorClassName}`}
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.5, repeat: Infinity, repeatType: 'reverse' }}
        />
      )}
    </div>
  )
}

interface StreamingContentProps {
  title: string
  content: string
  isStreaming: boolean
  progress?: number
  onClose?: () => void
}

/**
 * 流式内容显示组件
 * 带有标题、进度条和打字机效果
 */
export function StreamingContent({
  title,
  content,
  isStreaming,
  progress = 0,
  onClose
}: StreamingContentProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="bg-gray-900/95 backdrop-blur-sm border border-cyan-500/30 rounded-lg overflow-hidden"
    >
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800/50 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <motion.div
            className="w-2 h-2 rounded-full bg-cyan-400"
            animate={isStreaming ? { scale: [1, 1.2, 1] } : {}}
            transition={{ duration: 1, repeat: Infinity }}
          />
          <span className="text-sm text-gray-300">{title}</span>
        </div>
        {isStreaming && (
          <span className="text-xs text-cyan-400">{progress}%</span>
        )}
      </div>
      
      {/* 进度条 */}
      {isStreaming && (
        <div className="h-0.5 bg-gray-800">
          <motion.div
            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      )}
      
      {/* 内容区域 */}
      <div className="p-4 max-h-[400px] overflow-auto">
        <TypewriterText
          content={content}
          isStreaming={isStreaming}
          className="text-sm text-gray-200 leading-relaxed"
        />
      </div>
      
      {/* 底部状态 */}
      <div className="px-4 py-2 bg-gray-800/30 border-t border-gray-700 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {content.length} 字符
        </span>
        {!isStreaming && onClose && (
          <button
            onClick={onClose}
            className="text-xs text-cyan-400 hover:text-cyan-300"
          >
            收起
          </button>
        )}
      </div>
    </motion.div>
  )
}

export default TypewriterText
