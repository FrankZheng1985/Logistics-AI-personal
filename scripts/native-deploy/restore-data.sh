#!/bin/bash
# =============================================================================
# 数据恢复脚本
# 从 Docker 备份恢复数据到原生服务
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
PROJECT_DIR="/home/ubuntu/logistics-ai"
BACKUP_DIR="$1"

if [ -z "$BACKUP_DIR" ]; then
    echo -e "${RED}用法: $0 <备份目录路径>${NC}"
    echo "例如: $0 /home/ubuntu/backups/docker-migration-20250115_120000"
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}错误: 备份目录不存在: $BACKUP_DIR${NC}"
    exit 1
fi

echo -e "${BLUE}"
echo "=============================================="
echo "    从备份恢复数据"
echo "=============================================="
echo -e "${NC}"
echo "备份目录: $BACKUP_DIR"
echo ""

# 读取环境变量
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

DB_USER="${POSTGRES_USER:-admin}"
DB_NAME="${POSTGRES_DB:-logistics_ai}"

# -----------------------------------------------------------------------------
# 1. 恢复 PostgreSQL 数据
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[1/2] 恢复 PostgreSQL 数据...${NC}"

if [ -f "$BACKUP_DIR/postgres_backup.dump" ]; then
    echo "找到数据库备份文件，开始恢复..."
    
    # 先删除现有数据库并重建
    echo "  重建数据库..."
    sudo -u postgres psql <<EOF
-- 断开所有连接
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();

-- 删除并重建数据库
DROP DATABASE IF EXISTS ${DB_NAME};
CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
EOF

    # 恢复数据
    echo "  恢复数据中..."
    sudo -u postgres pg_restore -d "$DB_NAME" -v "$BACKUP_DIR/postgres_backup.dump" 2>&1 | tail -20
    
    echo -e "${GREEN}✓ PostgreSQL 数据恢复完成${NC}"
else
    echo -e "${YELLOW}⚠ 未找到 PostgreSQL 备份文件，跳过${NC}"
fi

# -----------------------------------------------------------------------------
# 2. 恢复 Redis 数据
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/2] 恢复 Redis 数据...${NC}"

if [ -f "$BACKUP_DIR/redis_dump.rdb" ] || [ -f "$BACKUP_DIR/redis_appendonly.aof" ]; then
    echo "找到 Redis 备份文件，开始恢复..."
    
    # 停止 Redis
    sudo systemctl stop redis-server
    
    # 复制备份文件
    if [ -f "$BACKUP_DIR/redis_dump.rdb" ]; then
        sudo cp "$BACKUP_DIR/redis_dump.rdb" /var/lib/redis/dump.rdb
        sudo chown redis:redis /var/lib/redis/dump.rdb
    fi
    
    if [ -f "$BACKUP_DIR/redis_appendonly.aof" ]; then
        sudo cp "$BACKUP_DIR/redis_appendonly.aof" /var/lib/redis/appendonly.aof
        sudo chown redis:redis /var/lib/redis/appendonly.aof
    fi
    
    # 启动 Redis
    sudo systemctl start redis-server
    
    echo -e "${GREEN}✓ Redis 数据恢复完成${NC}"
else
    echo -e "${YELLOW}⚠ 未找到 Redis 备份文件，跳过${NC}"
fi

# -----------------------------------------------------------------------------
# 完成
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}"
echo "=============================================="
echo "    数据恢复完成！"
echo "=============================================="
echo -e "${NC}"

echo ""
echo "验证数据:"
echo "  PostgreSQL: sudo -u postgres psql -d ${DB_NAME} -c '\\dt'"
echo "  Redis: redis-cli DBSIZE"
echo ""
