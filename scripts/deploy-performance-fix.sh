#!/bin/bash
# 本地运行的部署脚本
# 将性能优化推送到服务器并应用

set -e

SERVER="ubuntu@81.70.239.82"
KEY_FILE="/Users/fengzheng/Downloads/Cursor.pem"

echo "========================================="
echo "部署性能优化到服务器"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}步骤1: 上传优化文件到服务器...${NC}"
scp -i "$KEY_FILE" \
    database/migrations/040_optimize_ai_usage_logs_query.sql \
    scripts/apply-performance-optimization.sh \
    $SERVER:/home/ubuntu/logistics-ai-temp/

echo -e "${GREEN}✓ 文件上传完成${NC}"
echo ""

echo -e "${YELLOW}步骤2: 在服务器上应用优化...${NC}"
ssh -i "$KEY_FILE" $SERVER << 'ENDSSH'
    # 移动文件到正确位置
    sudo mv /home/ubuntu/logistics-ai-temp/040_optimize_ai_usage_logs_query.sql /home/ubuntu/logistics-ai/database/migrations/
    sudo mv /home/ubuntu/logistics-ai-temp/apply-performance-optimization.sh /home/ubuntu/logistics-ai/scripts/
    sudo chown ubuntu:ubuntu /home/ubuntu/logistics-ai/database/migrations/040_optimize_ai_usage_logs_query.sql
    sudo chown ubuntu:ubuntu /home/ubuntu/logistics-ai/scripts/apply-performance-optimization.sh
    sudo chmod +x /home/ubuntu/logistics-ai/scripts/apply-performance-optimization.sh
    
    # 执行优化脚本
    cd /home/ubuntu/logistics-ai
    bash scripts/apply-performance-optimization.sh
ENDSSH

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}部署完成!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "后续操作:"
echo "1. 在浏览器中强制刷新页面(Cmd+Shift+R 或 Ctrl+Shift+R)"
echo "2. 检查控制台是否还有错误"
echo "3. 如果还有问题,请告诉我具体的错误信息"
echo ""
