#!/bin/bash

# WordPress部署脚本
# 用于在生产服务器上部署WordPress网站

set -e

echo "🚀 开始部署 WordPress 网站..."

# 检查.env文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，从示例创建..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件设置数据库密码后重新运行此脚本"
    exit 1
fi

# 创建必要目录
echo "📁 创建目录..."
mkdir -p uploads

# 设置权限
echo "🔐 设置权限..."
chmod -R 755 themes/
chmod -R 755 plugins/
chmod -R 777 uploads/

# 停止旧容器
echo "🛑 停止旧容器..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# 拉取最新镜像
echo "📦 拉取最新镜像..."
docker-compose -f docker-compose.prod.yml pull

# 启动容器
echo "🚀 启动容器..."
docker-compose -f docker-compose.prod.yml up -d

# 等待启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查状态
echo "✅ 检查服务状态..."
docker-compose -f docker-compose.prod.yml ps

# 健康检查
echo "🏥 健康检查..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 | grep -q "200\|301\|302"; then
    echo "✅ WordPress 已成功启动!"
    echo ""
    echo "📝 下一步操作:"
    echo "   1. 访问 http://your-server-ip:8080 完成WordPress安装"
    echo "   2. 启用 Sysafari Logistics 主题"
    echo "   3. 启用 Sysafari Logistics Integration 插件"
    echo "   4. 配置API连接"
    echo "   5. 配置Nginx反向代理和SSL证书"
else
    echo "❌ WordPress 启动可能存在问题，请检查日志:"
    echo "   docker-compose -f docker-compose.prod.yml logs"
fi
