#!/bin/bash
# ============================================
# 物流获客AI - 监控和备份定时任务安装脚本
# 功能：配置crontab定时任务
# 使用方法：在服务器上执行 ./setup-monitoring.sh
# ============================================

set -e

SCRIPT_DIR="/home/ubuntu/logistics-ai/scripts"

echo "========================================"
echo "  物流获客AI - 定时任务配置"
echo "========================================"
echo ""

# 创建日志目录
mkdir -p /var/log/logistics-ai
mkdir -p /root/backups/postgres

# 设置脚本可执行权限
chmod +x ${SCRIPT_DIR}/backup/backup-database.sh
chmod +x ${SCRIPT_DIR}/backup/restore-database.sh
chmod +x ${SCRIPT_DIR}/monitoring/health-check.sh

echo "已设置脚本执行权限"

# 备份现有crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d).txt 2>/dev/null || true
echo "已备份现有crontab配置"

# 创建新的crontab配置
cat > /tmp/logistics_ai_cron << 'EOF'
# ============================================
# 物流获客AI - 定时任务配置
# ============================================

# 数据库自动备份 - 每天凌晨3点执行
0 3 * * * /home/ubuntu/logistics-ai/scripts/backup/backup-database.sh >> /var/log/logistics-ai/backup.log 2>&1

# 健康检查 - 每5分钟执行一次
*/5 * * * * /home/ubuntu/logistics-ai/scripts/monitoring/health-check.sh >> /var/log/logistics-ai/health-check.log 2>&1

# 日志清理 - 每周日凌晨4点清理超过30天的日志
0 4 * * 0 find /var/log/logistics-ai -name "*.log" -mtime +30 -delete

# Docker日志清理 - 每周一凌晨4点
0 4 * * 1 docker system prune -f >> /var/log/logistics-ai/docker-cleanup.log 2>&1

EOF

# 合并现有crontab（如果有）和新配置
(crontab -l 2>/dev/null | grep -v "logistics-ai" || true; cat /tmp/logistics_ai_cron) | crontab -

echo ""
echo "✅ 定时任务配置完成！"
echo ""
echo "已配置的定时任务："
echo "  • 数据库备份: 每天凌晨3点"
echo "  • 健康检查: 每5分钟"
echo "  • 日志清理: 每周日凌晨4点"
echo "  • Docker清理: 每周一凌晨4点"
echo ""
echo "查看当前crontab: crontab -l"
echo "查看备份日志: tail -f /var/log/logistics-ai/backup.log"
echo "查看健康检查日志: tail -f /var/log/logistics-ai/health-check.log"
