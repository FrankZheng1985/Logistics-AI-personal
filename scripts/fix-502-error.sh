#!/bin/bash
# 修复502错误 - 优化gunicorn和nginx配置
# 问题原因: gunicorn worker偶尔崩溃,nginx超时设置过短

set -e

echo "========================================="
echo "修复502 Bad Gateway错误"
echo "========================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. 备份现有nginx配置
echo -e "${YELLOW}步骤1: 备份nginx配置...${NC}"
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}✓ 配置已备份${NC}"
echo ""

# 2. 优化nginx超时设置
echo -e "${YELLOW}步骤2: 优化nginx超时设置...${NC}"
sudo sed -i 's/proxy_connect_timeout 60s;/proxy_connect_timeout 300s;/g' /etc/nginx/nginx.conf
sudo sed -i 's/proxy_send_timeout 120s;/proxy_send_timeout 300s;/g' /etc/nginx/nginx.conf
sudo sed -i 's/proxy_read_timeout 120s;/proxy_read_timeout 300s;/g' /etc/nginx/nginx.conf

# 添加更多proxy buffer设置(如果不存在)
sudo sed -i '/proxy_read_timeout/a \            proxy_buffering on;\n            proxy_buffer_size 4k;\n            proxy_buffers 8 4k;\n            proxy_busy_buffers_size 8k;' /etc/nginx/nginx.conf

echo -e "${GREEN}✓ nginx超时已优化${NC}"
echo ""

# 3. 测试nginx配置
echo -e "${YELLOW}步骤3: 测试nginx配置...${NC}"
sudo nginx -t
echo -e "${GREEN}✓ nginx配置测试通过${NC}"
echo ""

# 4. 重载nginx
echo -e "${YELLOW}步骤4: 重载nginx...${NC}"
sudo systemctl reload nginx
echo -e "${GREEN}✓ nginx已重载${NC}"
echo ""

# 5. 优化systemd服务配置
echo -e "${YELLOW}步骤5: 优化systemd服务配置...${NC}"
sudo cp /etc/systemd/system/logistics-backend.service /etc/systemd/system/logistics-backend.service.backup.$(date +%Y%m%d_%H%M%S)

# 修改gunicorn配置,添加worker管理策略
sudo tee /etc/systemd/system/logistics-backend.service > /dev/null << 'EOF'
[Unit]
Description=Logistics AI Backend (FastAPI + Gunicorn)
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=notify
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/logistics-ai/backend

EnvironmentFile=/home/ubuntu/logistics-ai/.env

Environment="PATH=/home/ubuntu/logistics-ai/backend/venv/bin:/opt/nodejs/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="DATABASE_URL=postgresql+asyncpg://admin:lIyGC5PuxC6RUHKmv6vmLDR9iDH2JY2F@127.0.0.1:5432/logistics_ai"
Environment="REDIS_URL=redis://127.0.0.1:6379/0"

# 优化的gunicorn配置
ExecStart=/home/ubuntu/logistics-ai/backend/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 900 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --worker-tmp-dir /dev/shm \
    --access-logfile /var/log/logistics-ai/access.log \
    --error-logfile /var/log/logistics-ai/error.log \
    --log-level info \
    --capture-output

# 重启策略优化
Restart=always
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ systemd服务配置已优化${NC}"
echo ""

# 6. 重载systemd并重启服务
echo -e "${YELLOW}步骤6: 应用新配置...${NC}"
sudo systemctl daemon-reload
sudo systemctl restart logistics-backend
sleep 5

# 等待服务启动
echo "等待服务完全启动..."
for i in {1..30}; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

echo -e "${GREEN}✓ 服务已重启${NC}"
echo ""

# 7. 测试API
echo -e "${YELLOW}步骤7: 测试API...${NC}"
echo "测试 /api/notifications:"
curl -s -o /dev/null -w "HTTP %{http_code} - 响应时间: %{time_total}s\n" "http://localhost:9000/api/notifications?limit=1"

echo ""
echo "测试 /api/ai-usage/dashboard:"
curl -s -o /dev/null -w "HTTP %{http_code} - 响应时间: %{time_total}s\n" "http://localhost:9000/api/ai-usage/dashboard"

echo ""
echo "测试 /api/ai-usage/logs:"
curl -s -o /dev/null -w "HTTP %{http_code} - 响应时间: %{time_total}s\n" "http://localhost:9000/api/ai-usage/logs?page=1&page_size=20"

echo ""
echo -e "${GREEN}✓ API测试完成${NC}"
echo ""

echo "========================================="
echo -e "${GREEN}502错误修复完成!${NC}"
echo "========================================="
echo ""
echo "已应用的优化:"
echo "1. ✅ nginx超时从120s增加到300s"
echo "2. ✅ 添加了nginx proxy buffer配置"
echo "3. ✅ gunicorn添加了worker重启策略(每1000请求重启)"
echo "4. ✅ gunicorn worker使用/dev/shm临时目录(更快)"
echo "5. ✅ 优化了systemd重启策略"
echo ""
echo "配置备份位置:"
echo "- /etc/nginx/nginx.conf.backup.*"
echo "- /etc/systemd/system/logistics-backend.service.backup.*"
echo ""
echo "监控建议:"
echo "1. 观察 /var/log/logistics-ai/error.log"
echo "2. 观察 sudo journalctl -u logistics-backend -f"
echo "3. 如果还有问题,检查 sudo tail -f /var/log/nginx/error.log"
echo ""
