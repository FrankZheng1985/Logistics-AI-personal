#!/bin/bash
# 应用性能优化脚本
# 用途:修复API超时问题,优化AI用量日志查询性能

set -e

echo "========================================="
echo "AI获客系统 - 性能优化部署"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="/home/ubuntu/logistics-ai"
DB_NAME="logistics_ai"

# 检查是否在服务器上
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}错误: 找不到项目目录 $PROJECT_DIR${NC}"
    echo "请在服务器上运行此脚本"
    exit 1
fi

cd $PROJECT_DIR

echo -e "${YELLOW}步骤1: 备份数据库...${NC}"
BACKUP_FILE="backup_before_optimization_$(date +%Y%m%d_%H%M%S).sql"
sudo -u postgres pg_dump $DB_NAME > "/home/ubuntu/$BACKUP_FILE"
echo -e "${GREEN}✓ 数据库已备份到: /home/ubuntu/$BACKUP_FILE${NC}"
echo ""

echo -e "${YELLOW}步骤2: 应用性能优化SQL...${NC}"
sudo -u postgres psql -d $DB_NAME -f database/migrations/040_optimize_ai_usage_logs_query.sql
echo -e "${GREEN}✓ 性能优化SQL已应用${NC}"
echo ""

echo -e "${YELLOW}步骤3: 检查AI用量日志表状态...${NC}"
sudo -u postgres psql -d $DB_NAME << 'EOF'
-- 显示表的统计信息
SELECT 
    relname AS table_name,
    n_live_tup AS row_count,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
WHERE relname = 'ai_usage_logs';

-- 显示所有索引
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'ai_usage_logs'
ORDER BY indexname;
EOF
echo -e "${GREEN}✓ 表状态检查完成${NC}"
echo ""

echo -e "${YELLOW}步骤4: 测试API性能...${NC}"
echo "测试 /api/notifications :"
time curl -s -o /dev/null -w "HTTP状态码: %{http_code}, 响应时间: %{time_total}s\n" http://localhost:9000/api/notifications?limit=1

echo ""
echo "测试 /api/ai-usage/dashboard :"
time curl -s -o /dev/null -w "HTTP状态码: %{http_code}, 响应时间: %{time_total}s\n" http://localhost:9000/api/ai-usage/dashboard

echo ""
echo "测试 /api/ai-usage/logs :"
time curl -s -o /dev/null -w "HTTP状态码: %{http_code}, 响应时间: %{time_total}s\n" "http://localhost:9000/api/ai-usage/logs?page=1&page_size=20"

echo ""
echo -e "${GREEN}✓ API性能测试完成${NC}"
echo ""

echo "========================================="
echo -e "${GREEN}性能优化部署完成!${NC}"
echo "========================================="
echo ""
echo "建议操作:"
echo "1. 在浏览器中按 Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows) 强制刷新页面"
echo "2. 清除浏览器缓存"
echo "3. 如果问题仍存在,重启后端服务: sudo systemctl restart logistics-backend"
echo ""
echo "数据备份位置: /home/ubuntu/$BACKUP_FILE"
echo ""
