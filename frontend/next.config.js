/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  
  // 图片域名配置
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'https',
        hostname: '*.myqcloud.com',  // 腾讯云COS
      },
      {
        protocol: 'https',
        hostname: '*.cos.*.myqcloud.com',  // COS完整域名
      },
      {
        protocol: 'https',
        hostname: 'ai.xianfeng-eu.com',  // 生产域名
      },
    ],
    // 图片优化
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
  
  // 环境变量（服务端和客户端都可用）
  env: {
    NEXT_PUBLIC_APP_NAME: '物流获客AI',
    NEXT_PUBLIC_APP_VERSION: '1.0.0',
  },
  
  // 编译优化
  compiler: {
    // 生产环境移除console.log
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },
  
  // 实验性功能
  experimental: {
    // 优化包导入
    optimizePackageImports: ['lucide-react', 'framer-motion', 'recharts'],
  },
  
  // 重定向规则
  async redirects() {
    return [
      {
        source: '/home',
        destination: '/dashboard',
        permanent: true,
      },
    ]
  },
  
  // API代理配置（本地开发用）
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
  
  // 请求头配置
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ]
  },
}

module.exports = nextConfig
