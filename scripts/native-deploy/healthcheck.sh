#!/bin/bash
# =============================================================================
# 健康检查和自动恢复脚本
# 定期检查所有服务状态，如果发现问题自动重启
# 建议添加到 crontab: */5 * * * * /home/ubuntu/logistics-ai/scripts/native-deploy/healthcheck.sh
# =============================================================================

set -e

# 颜色（用于终端输出）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
LOG_FILE="/var/log/logistics-ai/healthcheck.log"
ALERT_EMAIL=""  # 设置邮箱地址接收告警

# 时间戳函数
timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# 日志函数
log() {
    echo "[$(timestamp)] $1" | tee -a "$LOG_FILE"
}

# 发送告警（如果配置了邮箱）
send_alert() {
    local subject="$1"
    local message="$2"
    
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "[物流获客AI] $subject" "$ALERT_EMAIL" 2>/dev/null || true
    fi
}

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

log "========== 开始健康检查 =========="

# 状态统计
ISSUES_FOUND=0

# -----------------------------------------------------------------------------
# 1. 检查 PostgreSQL
# -----------------------------------------------------------------------------
check_postgresql() {
    log "检查 PostgreSQL..."
    
    if systemctl is-active --quiet postgresql; then
        # 进一步检查是否可以连接
        if sudo -u postgres psql -c "SELECT 1" > /dev/null 2>&1; then
            log "  ✓ PostgreSQL 运行正常"
            return 0
        else
            log "  ✗ PostgreSQL 运行但无法连接"
            return 1
        fi
    else
        log "  ✗ PostgreSQL 未运行"
        return 1
    fi
}

if ! check_postgresql; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    log "  → 尝试重启 PostgreSQL..."
    sudo systemctl restart postgresql
    sleep 5
    
    if check_postgresql; then
        log "  → PostgreSQL 重启成功"
        send_alert "PostgreSQL 已自动恢复" "PostgreSQL 服务检测到异常，已自动重启恢复。"
    else
        log "  → PostgreSQL 重启失败！需要人工干预"
        send_alert "PostgreSQL 故障" "PostgreSQL 服务无法自动恢复，请立即检查！"
    fi
fi

# -----------------------------------------------------------------------------
# 2. 检查 Redis
# -----------------------------------------------------------------------------
check_redis() {
    log "检查 Redis..."
    
    if systemctl is-active --quiet redis-server; then
        # 检查是否可以 PING
        if redis-cli ping > /dev/null 2>&1; then
            log "  ✓ Redis 运行正常"
            return 0
        else
            log "  ✗ Redis 运行但无法 PING"
            return 1
        fi
    else
        log "  ✗ Redis 未运行"
        return 1
    fi
}

if ! check_redis; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    log "  → 尝试重启 Redis..."
    sudo systemctl restart redis-server
    sleep 3
    
    if check_redis; then
        log "  → Redis 重启成功"
        send_alert "Redis 已自动恢复" "Redis 服务检测到异常，已自动重启恢复。"
    else
        log "  → Redis 重启失败！需要人工干预"
        send_alert "Redis 故障" "Redis 服务无法自动恢复，请立即检查！"
    fi
fi

# -----------------------------------------------------------------------------
# 3. 检查后端服务
# -----------------------------------------------------------------------------
check_backend() {
    log "检查后端服务..."
    
    if systemctl is-active --quiet logistics-backend; then
        # 检查健康端点
        if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
            log "  ✓ 后端服务运行正常"
            return 0
        else
            log "  ✗ 后端服务运行但健康检查失败"
            return 1
        fi
    else
        log "  ✗ 后端服务未运行"
        return 1
    fi
}

if ! check_backend; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    log "  → 尝试重启后端服务..."
    sudo systemctl restart logistics-backend
    sleep 10  # 后端启动较慢
    
    if check_backend; then
        log "  → 后端服务重启成功"
        send_alert "后端服务已自动恢复" "后端服务检测到异常，已自动重启恢复。"
    else
        log "  → 后端服务重启失败！需要人工干预"
        send_alert "后端服务故障" "后端服务无法自动恢复，请立即检查！"
    fi
fi

# -----------------------------------------------------------------------------
# 4. 检查前端服务 (PM2)
# -----------------------------------------------------------------------------
check_frontend() {
    log "检查前端服务..."
    
    # 检查 PM2 进程
    if pm2 list | grep -q "logistics-frontend" | grep -q "online"; then
        # 检查是否可以访问
        if curl -sf http://127.0.0.1:3000 > /dev/null 2>&1; then
            log "  ✓ 前端服务运行正常"
            return 0
        else
            log "  ✗ 前端服务运行但无法访问"
            return 1
        fi
    else
        log "  ✗ 前端服务未运行或状态异常"
        return 1
    fi
}

if ! check_frontend; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    log "  → 尝试重启前端服务..."
    cd /home/ubuntu/logistics-ai/frontend
    pm2 reload ecosystem.config.js 2>/dev/null || pm2 start ecosystem.config.js
    sleep 5
    
    if check_frontend; then
        log "  → 前端服务重启成功"
        send_alert "前端服务已自动恢复" "前端服务检测到异常，已自动重启恢复。"
    else
        log "  → 前端服务重启失败！需要人工干预"
        send_alert "前端服务故障" "前端服务无法自动恢复，请立即检查！"
    fi
fi

# -----------------------------------------------------------------------------
# 5. 检查 Nginx
# -----------------------------------------------------------------------------
check_nginx() {
    log "检查 Nginx..."
    
    if systemctl is-active --quiet nginx; then
        log "  ✓ Nginx 运行正常"
        return 0
    else
        log "  ✗ Nginx 未运行"
        return 1
    fi
}

if ! check_nginx; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    log "  → 尝试重启 Nginx..."
    sudo nginx -t && sudo systemctl restart nginx
    sleep 2
    
    if check_nginx; then
        log "  → Nginx 重启成功"
        send_alert "Nginx 已自动恢复" "Nginx 服务检测到异常，已自动重启恢复。"
    else
        log "  → Nginx 重启失败！需要人工干预"
        send_alert "Nginx 故障" "Nginx 服务无法自动恢复，请立即检查！"
    fi
fi

# -----------------------------------------------------------------------------
# 6. 检查磁盘空间
# -----------------------------------------------------------------------------
check_disk() {
    log "检查磁盘空间..."
    
    # 获取根分区使用率
    DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$DISK_USAGE" -lt 85 ]; then
        log "  ✓ 磁盘使用率: ${DISK_USAGE}%"
        return 0
    elif [ "$DISK_USAGE" -lt 95 ]; then
        log "  ⚠ 磁盘使用率: ${DISK_USAGE}% (警告)"
        send_alert "磁盘空间警告" "磁盘使用率已达 ${DISK_USAGE}%，请及时清理！"
        return 0
    else
        log "  ✗ 磁盘使用率: ${DISK_USAGE}% (危险)"
        send_alert "磁盘空间危险" "磁盘使用率已达 ${DISK_USAGE}%，系统可能很快无法运行！"
        return 1
    fi
}

check_disk || ISSUES_FOUND=$((ISSUES_FOUND + 1))

# -----------------------------------------------------------------------------
# 7. 检查内存使用
# -----------------------------------------------------------------------------
check_memory() {
    log "检查内存使用..."
    
    # 获取内存使用率
    MEM_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100)}')
    
    if [ "$MEM_USAGE" -lt 85 ]; then
        log "  ✓ 内存使用率: ${MEM_USAGE}%"
        return 0
    elif [ "$MEM_USAGE" -lt 95 ]; then
        log "  ⚠ 内存使用率: ${MEM_USAGE}% (警告)"
        return 0
    else
        log "  ✗ 内存使用率: ${MEM_USAGE}% (危险)"
        send_alert "内存使用危险" "内存使用率已达 ${MEM_USAGE}%，可能导致 OOM！"
        return 1
    fi
}

check_memory || ISSUES_FOUND=$((ISSUES_FOUND + 1))

# -----------------------------------------------------------------------------
# 总结
# -----------------------------------------------------------------------------
log "========== 健康检查完成 =========="

if [ $ISSUES_FOUND -eq 0 ]; then
    log "所有服务运行正常 ✓"
else
    log "发现 ${ISSUES_FOUND} 个问题"
fi

exit 0
