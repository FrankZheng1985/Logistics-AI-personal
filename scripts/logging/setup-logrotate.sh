#!/bin/bash
# ============================================
# 物流获客AI - 日志轮转安装脚本
# 功能：配置系统日志轮转
# 使用方法：在服务器上执行 ./setup-logrotate.sh
# ============================================

set -e

SCRIPT_DIR="/root/logistics-ai/scripts"

echo "========================================"
echo "  物流获客AI - 日志轮转配置"
echo "========================================"
echo ""

# 检查logrotate是否安装
if ! command -v logrotate &> /dev/null; then
    echo "安装 logrotate..."
    apt-get update && apt-get install -y logrotate
fi

# 创建日志目录
mkdir -p /var/log/logistics-ai

# 复制日志轮转配置
cp ${SCRIPT_DIR}/logging/logrotate.conf /etc/logrotate.d/logistics-ai

echo "✅ 日志轮转配置已安装到 /etc/logrotate.d/logistics-ai"

# 配置Docker日志驱动（限制日志大小）
echo ""
echo "配置Docker日志驱动..."

# 创建Docker daemon配置
cat > /etc/docker/daemon.json << 'EOF'
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "50m",
        "max-file": "3"
    }
}
EOF

echo "✅ Docker日志配置已更新"
echo ""
echo "⚠️  重要：需要重启Docker服务以应用日志配置"
echo "执行命令: systemctl restart docker"
echo ""
echo "日志轮转配置说明："
echo "  • 应用日志: 每天轮转，保留14天，自动压缩"
echo "  • Docker日志: 每个容器最大50MB，保留3个文件"
echo ""
echo "手动测试日志轮转: logrotate -f /etc/logrotate.d/logistics-ai"
