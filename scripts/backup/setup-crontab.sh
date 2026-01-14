#!/bin/bash
# ============================================
# 物流获客AI - 定时任务配置脚本
# 功能：配置数据库备份和系统清理的cron任务
# ============================================

set -e

# 配置变量
PROJECT_DIR="/home/ubuntu/logistics-ai"
BACKUP_SCRIPT="${PROJECT_DIR}/scripts/backup/backup-database.sh"
LOG_DIR="/home/ubuntu/logs/cron"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 创建日志目录
mkdir -p ${LOG_DIR}

log "开始配置定时任务..."

# 确保备份脚本可执行
chmod +x ${BACKUP_SCRIPT} 2>/dev/null || true

# 创建临时crontab文件
TEMP_CRONTAB=$(mktemp)

# 获取当前用户的crontab（如果存在）
crontab -l 2>/dev/null | grep -v "backup-database.sh" | grep -v "# 物流获客AI" > ${TEMP_CRONTAB} || true

# 添加物流获客AI的定时任务
cat >> ${TEMP_CRONTAB} << EOF

# ============================================
# 物流获客AI - 自动化任务
# ============================================

# 每天凌晨3点执行数据库备份
0 3 * * * ${BACKUP_SCRIPT} >> ${LOG_DIR}/backup.log 2>&1

# 每周日凌晨4点清理Docker日志和无用镜像
0 4 * * 0 docker system prune -f >> ${LOG_DIR}/cleanup.log 2>&1

# 每天凌晨5点清理超过30天的cron日志
0 5 * * * find ${LOG_DIR} -name "*.log" -mtime +30 -delete

EOF

# 安装新的crontab
crontab ${TEMP_CRONTAB}

# 清理临时文件
rm -f ${TEMP_CRONTAB}

log "定时任务配置完成！"
log "已添加的任务："
log "  - 每天03:00: 数据库自动备份"
log "  - 每周日04:00: Docker系统清理"
log "  - 每天05:00: 清理过期日志"

# 显示当前crontab
log "当前crontab配置："
crontab -l | grep -A 100 "物流获客AI" || echo "  (无物流获客AI相关任务)"
