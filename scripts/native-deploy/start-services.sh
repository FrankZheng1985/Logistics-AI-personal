#!/bin/bash
# =============================================================================
# 启动所有服务脚本
# 按正确顺序启动所有原生部署的服务
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "=============================================="
echo "    启动物流获客AI所有服务"
echo "=============================================="
echo -e "${NC}"

# 检查是否有 sudo 权限
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
else
    SUDO=""
fi

# -----------------------------------------------------------------------------
# 1. 启动 PostgreSQL
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[1/5] 启动 PostgreSQL...${NC}"
$SUDO systemctl start postgresql
$SUDO systemctl enable postgresql
sleep 2

if $SUDO systemctl is-active --quiet postgresql; then
    echo -e "${GREEN}✓ PostgreSQL 已启动${NC}"
else
    echo -e "${RED}✗ PostgreSQL 启动失败${NC}"
    exit 1
fi

# -----------------------------------------------------------------------------
# 2. 启动 Redis
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/5] 启动 Redis...${NC}"
$SUDO systemctl start redis-server
$SUDO systemctl enable redis-server
sleep 2

if $SUDO systemctl is-active --quiet redis-server; then
    echo -e "${GREEN}✓ Redis 已启动${NC}"
else
    echo -e "${RED}✗ Redis 启动失败${NC}"
    exit 1
fi

# -----------------------------------------------------------------------------
# 3. 启动后端服务
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/5] 启动后端服务...${NC}"
$SUDO systemctl start logistics-backend
$SUDO systemctl enable logistics-backend
sleep 5

if $SUDO systemctl is-active --quiet logistics-backend; then
    echo -e "${GREEN}✓ 后端服务已启动${NC}"
else
    echo -e "${RED}✗ 后端服务启动失败${NC}"
    echo "查看日志: sudo journalctl -u logistics-backend -n 50"
    exit 1
fi

# -----------------------------------------------------------------------------
# 4. 启动前端服务 (PM2)
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/5] 启动前端服务...${NC}"
cd /home/ubuntu/logistics-ai/frontend

# 检查 PM2 是否已有进程
if pm2 list | grep -q "logistics-frontend"; then
    pm2 reload ecosystem.config.js
else
    pm2 start ecosystem.config.js
fi

pm2 save
sleep 3

if pm2 list | grep -q "online"; then
    echo -e "${GREEN}✓ 前端服务已启动${NC}"
else
    echo -e "${RED}✗ 前端服务启动失败${NC}"
    echo "查看日志: pm2 logs logistics-frontend"
    exit 1
fi

# -----------------------------------------------------------------------------
# 5. 启动 Nginx
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[5/5] 启动 Nginx...${NC}"

# 测试配置
if $SUDO nginx -t; then
    $SUDO systemctl start nginx
    $SUDO systemctl enable nginx
    
    if $SUDO systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✓ Nginx 已启动${NC}"
    else
        echo -e "${RED}✗ Nginx 启动失败${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Nginx 配置错误${NC}"
    exit 1
fi

# -----------------------------------------------------------------------------
# 完成
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}"
echo "=============================================="
echo "    所有服务已启动！"
echo "=============================================="
echo -e "${NC}"

echo ""
echo "服务状态:"
echo "-------------------------------------------"
echo -e "PostgreSQL:  $($SUDO systemctl is-active postgresql && echo -e '${GREEN}运行中${NC}' || echo -e '${RED}已停止${NC}')"
echo -e "Redis:       $($SUDO systemctl is-active redis-server && echo -e '${GREEN}运行中${NC}' || echo -e '${RED}已停止${NC}')"
echo -e "后端:        $($SUDO systemctl is-active logistics-backend && echo -e '${GREEN}运行中${NC}' || echo -e '${RED}已停止${NC}')"
echo -e "前端:        $(pm2 list | grep -q 'online' && echo -e '${GREEN}运行中${NC}' || echo -e '${RED}已停止${NC}')"
echo -e "Nginx:       $($SUDO systemctl is-active nginx && echo -e '${GREEN}运行中${NC}' || echo -e '${RED}已停止${NC}')"
echo ""
echo "访问地址:"
echo "  本地: http://127.0.0.1:9000"
echo "  公网: https://ai.sysafari.com (如果已配置域名)"
echo ""
echo "管理命令:"
echo "  查看后端日志: sudo journalctl -u logistics-backend -f"
echo "  查看前端日志: pm2 logs logistics-frontend"
echo "  查看所有状态: sudo systemctl status postgresql redis-server logistics-backend nginx"
echo ""
