#!/bin/bash
# =============================================================================
# Docker 数据备份脚本
# 在迁移到原生部署前，备份所有 Docker 容器中的数据
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
BACKUP_DIR="/home/ubuntu/backups/docker-migration-$(date +%Y%m%d_%H%M%S)"
PROJECT_DIR="/home/ubuntu/logistics-ai"

echo -e "${GREEN}=== Docker 数据备份脚本 ===${NC}"
echo "备份目录: $BACKUP_DIR"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# -----------------------------------------------------------------------------
# 1. 备份 PostgreSQL 数据
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[1/4] 备份 PostgreSQL 数据...${NC}"

if docker ps | grep -q logistics-ai-db; then
    # 获取数据库凭据
    source "$PROJECT_DIR/.env" 2>/dev/null || true
    DB_USER="${POSTGRES_USER:-admin}"
    DB_NAME="${POSTGRES_DB:-logistics_ai}"
    
    # 导出数据库
    docker exec logistics-ai-db pg_dump -U "$DB_USER" -d "$DB_NAME" -F c -f /tmp/backup.dump
    docker cp logistics-ai-db:/tmp/backup.dump "$BACKUP_DIR/postgres_backup.dump"
    docker exec logistics-ai-db rm /tmp/backup.dump
    
    # 同时导出 SQL 格式（便于查看）
    docker exec logistics-ai-db pg_dump -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_DIR/postgres_backup.sql"
    
    echo -e "${GREEN}✓ PostgreSQL 备份完成${NC}"
    echo "  - $BACKUP_DIR/postgres_backup.dump (二进制格式)"
    echo "  - $BACKUP_DIR/postgres_backup.sql (SQL 格式)"
else
    echo -e "${RED}✗ PostgreSQL 容器未运行，跳过备份${NC}"
fi

# -----------------------------------------------------------------------------
# 2. 备份 Redis 数据
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/4] 备份 Redis 数据...${NC}"

if docker ps | grep -q logistics-ai-redis; then
    # 触发 RDB 保存
    docker exec logistics-ai-redis redis-cli BGSAVE
    sleep 2  # 等待保存完成
    
    # 复制 RDB 文件
    docker cp logistics-ai-redis:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb" 2>/dev/null || \
        echo "  注意: 没有找到 RDB 文件，可能 Redis 中没有数据"
    
    # 复制 AOF 文件（如果存在）
    docker cp logistics-ai-redis:/data/appendonly.aof "$BACKUP_DIR/redis_appendonly.aof" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Redis 备份完成${NC}"
else
    echo -e "${RED}✗ Redis 容器未运行，跳过备份${NC}"
fi

# -----------------------------------------------------------------------------
# 3. 备份配置文件
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/4] 备份配置文件...${NC}"

mkdir -p "$BACKUP_DIR/config"

# 备份 .env 文件
if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$BACKUP_DIR/config/.env"
    echo "  ✓ .env 文件已备份"
fi

# 备份 nginx.conf
if [ -f "$PROJECT_DIR/nginx.conf" ]; then
    cp "$PROJECT_DIR/nginx.conf" "$BACKUP_DIR/config/nginx.conf"
    echo "  ✓ nginx.conf 已备份"
fi

# 备份 docker-compose 文件
cp "$PROJECT_DIR/docker-compose.prod.yml" "$BACKUP_DIR/config/" 2>/dev/null || true
cp "$PROJECT_DIR/docker-compose.yml" "$BACKUP_DIR/config/" 2>/dev/null || true

echo -e "${GREEN}✓ 配置文件备份完成${NC}"

# -----------------------------------------------------------------------------
# 4. 记录当前状态
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/4] 记录当前系统状态...${NC}"

# 记录 Docker 容器状态
docker ps -a > "$BACKUP_DIR/docker_containers.txt"
docker images > "$BACKUP_DIR/docker_images.txt"
docker volume ls > "$BACKUP_DIR/docker_volumes.txt"

# 记录磁盘使用
df -h > "$BACKUP_DIR/disk_usage.txt"

echo -e "${GREEN}✓ 系统状态已记录${NC}"

# -----------------------------------------------------------------------------
# 完成
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}备份完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "备份位置: $BACKUP_DIR"
echo ""
echo "备份内容:"
ls -la "$BACKUP_DIR"
echo ""
echo -e "${YELLOW}重要提示:${NC}"
echo "1. 请确认备份文件完整后再进行迁移"
echo "2. 建议将备份目录复制到其他位置以防万一"
echo "3. 可以使用以下命令验证 PostgreSQL 备份:"
echo "   pg_restore --list $BACKUP_DIR/postgres_backup.dump"
echo ""
