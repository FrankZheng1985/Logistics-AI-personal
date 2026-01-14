#!/bin/bash
# ============================================
# 物流获客AI - 数据库恢复脚本
# 功能：从备份文件恢复PostgreSQL数据库
# 使用方法：./restore-database.sh <备份文件路径>
# ============================================

set -e

# 数据库配置
DB_CONTAINER="logistics-ai-db"
DB_NAME="logistics_ai"
DB_USER="admin"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 检查参数
if [ -z "$1" ]; then
    echo "用法: $0 <备份文件路径>"
    echo "示例: $0 /root/backups/postgres/logistics_ai_backup_20260114_120000.sql.gz"
    echo ""
    echo "可用的备份文件:"
    ls -la /home/ubuntu/backups/postgres/*.sql.gz 2>/dev/null || echo "  无备份文件"
    exit 1
fi

BACKUP_FILE="$1"

# 检查文件是否存在
if [ ! -f "${BACKUP_FILE}" ]; then
    log "错误：备份文件不存在: ${BACKUP_FILE}"
    exit 1
fi

# 确认操作
echo "⚠️  警告：此操作将覆盖当前数据库中的所有数据！"
echo "备份文件: ${BACKUP_FILE}"
read -p "确认要恢复吗？(输入 'yes' 确认): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    log "操作已取消"
    exit 0
fi

log "开始恢复数据库..."

# 判断是否是压缩文件
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    log "解压备份文件..."
    gunzip -c ${BACKUP_FILE} | docker exec -i ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME}
else
    docker exec -i ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} < ${BACKUP_FILE}
fi

log "数据库恢复完成！"
log "建议：重启后端服务以确保连接正常"
echo ""
echo "重启命令: docker-compose -f docker-compose.prod.yml restart backend"
