// =============================================================================
// PM2 配置文件 - Next.js 前端服务
// =============================================================================

module.exports = {
  apps: [
    {
      // 应用名称
      name: 'logistics-frontend',
      
      // 启动脚本
      script: 'node',
      args: 'server.js',
      
      // 工作目录
      cwd: '/home/ubuntu/logistics-ai/frontend',
      
      // 实例数量（cluster 模式）
      // 'max' 会使用所有 CPU 核心，这里设置为 2 节省资源
      instances: 2,
      
      // 执行模式：cluster 模式支持负载均衡
      exec_mode: 'cluster',
      
      // 环境变量
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
        HOSTNAME: '0.0.0.0',
        // API 通过 Nginx 代理
        NEXT_PUBLIC_API_URL: '/api'
      },
      
      // 自动重启配置
      autorestart: true,
      
      // 文件变化时自动重启（生产环境关闭）
      watch: false,
      
      // 最大内存重启阈值
      max_memory_restart: '500M',
      
      // 重启延迟
      restart_delay: 1000,
      
      // 最大重启次数（超过后停止）
      max_restarts: 10,
      
      // 最小运行时间（毫秒），低于此时间的重启被视为异常
      min_uptime: '10s',
      
      // 日志配置
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      error_file: '/var/log/logistics-ai/frontend-error.log',
      out_file: '/var/log/logistics-ai/frontend-out.log',
      merge_logs: true,
      
      // 日志轮转（最多保留 10 个文件，每个最大 10M）
      log_type: 'json',
      
      // 优雅关闭
      kill_timeout: 5000,
      listen_timeout: 10000,
      
      // 健康检查（可选，需要安装 pm2-health 插件）
      // health_check: {
      //   enabled: true,
      //   endpoint: 'http://localhost:3000',
      //   interval: 30000
      // }
    }
  ],
  
  // 部署配置（可选，用于 pm2 deploy）
  deploy: {
    production: {
      user: 'ubuntu',
      host: '81.70.239.82',
      ref: 'origin/main',
      repo: 'git@github.com:yourusername/logistics-ai.git',
      path: '/home/ubuntu/logistics-ai',
      'pre-deploy-local': '',
      'post-deploy': 'cd frontend && npm ci --legacy-peer-deps && npm run build && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
};
