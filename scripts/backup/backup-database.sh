#!/bin/bash
# ============================================
# 物流获客AI - 数据库自动备份脚本
# 功能：定期备份PostgreSQL数据库到本地和腾讯云COS
# 使用方法：通过crontab定时执行
# ============================================

set -e

# 配置变量
BACKUP_DIR="/root/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="logistics_ai_backup_${DATE}.sql"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

# 数据库配置
DB_CONTAINER="logistics-ai-db"
DB_NAME="logistics_ai"
DB_USER="admin"

# 保留天数
KEEP_DAYS=7

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 创建备份目录
mkdir -p ${BACKUP_DIR}

log "开始备份数据库..."

# 执行数据库备份
docker exec ${DB_CONTAINER} pg_dump -U ${DB_USER} -d ${DB_NAME} > ${BACKUP_DIR}/${BACKUP_FILE}

# 检查备份文件
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    # 压缩备份文件
    gzip ${BACKUP_DIR}/${BACKUP_FILE}
    
    # 获取文件大小
    BACKUP_SIZE=$(du -h ${BACKUP_DIR}/${BACKUP_FILE_GZ} | cut -f1)
    log "备份完成: ${BACKUP_FILE_GZ} (${BACKUP_SIZE})"
    
    # 删除旧备份（保留最近N天）
    find ${BACKUP_DIR} -name "logistics_ai_backup_*.sql.gz" -mtime +${KEEP_DAYS} -delete
    log "已清理${KEEP_DAYS}天前的旧备份"
    
    # 统计当前备份数量
    BACKUP_COUNT=$(ls -1 ${BACKUP_DIR}/logistics_ai_backup_*.sql.gz 2>/dev/null | wc -l)
    log "当前备份文件数量: ${BACKUP_COUNT}"
else
    log "错误：备份失败，文件未生成"
    exit 1
fi

# 可选：上传到腾讯云COS（需要配置COSCMD）
# if command -v coscmd &> /dev/null; then
#     log "上传备份到腾讯云COS..."
#     coscmd upload ${BACKUP_DIR}/${BACKUP_FILE_GZ} /backups/postgres/
#     log "COS上传完成"
# fi

log "数据库备份任务完成！"
