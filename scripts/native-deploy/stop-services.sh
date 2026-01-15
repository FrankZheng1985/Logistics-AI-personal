#!/bin/bash
# =============================================================================
# 停止所有服务脚本
# 按正确顺序停止所有原生部署的服务
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}正在停止所有服务...${NC}"

# 检查是否有 sudo 权限
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
else
    SUDO=""
fi

# 1. 停止 Nginx（先停止入口）
echo "停止 Nginx..."
$SUDO systemctl stop nginx 2>/dev/null || true

# 2. 停止前端
echo "停止前端服务..."
pm2 stop all 2>/dev/null || true

# 3. 停止后端
echo "停止后端服务..."
$SUDO systemctl stop logistics-backend 2>/dev/null || true

# 4. 停止 Redis
echo "停止 Redis..."
$SUDO systemctl stop redis-server 2>/dev/null || true

# 5. 停止 PostgreSQL
echo "停止 PostgreSQL..."
$SUDO systemctl stop postgresql 2>/dev/null || true

echo -e "${GREEN}所有服务已停止${NC}"
