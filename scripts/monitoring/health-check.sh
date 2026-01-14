#!/bin/bash
# ============================================
# 物流获客AI - 服务健康监控脚本
# 功能：检查所有服务状态，异常时发送告警
# 使用方法：通过crontab每5分钟执行一次
# ============================================

set -e

# 配置
LOG_FILE="/var/log/logistics-ai/health-check.log"
ALERT_FILE="/tmp/logistics_ai_alert_sent"
SERVER_IP="81.70.239.82"

# 服务端点
BACKEND_URL="http://127.0.0.1:8000/health"
FRONTEND_URL="http://127.0.0.1:3000"
NGINX_URL="http://127.0.0.1:80/health"

# 企业微信告警配置（可选）
# WECHAT_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"

# 创建日志目录
mkdir -p $(dirname ${LOG_FILE})

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

# 发送告警函数
send_alert() {
    local message="$1"
    local service="$2"
    
    log "🚨 告警: ${message}"
    
    # 防止重复告警（1小时内同一服务只告警一次）
    if [ -f "${ALERT_FILE}_${service}" ]; then
        LAST_ALERT=$(cat "${ALERT_FILE}_${service}")
        CURRENT_TIME=$(date +%s)
        DIFF=$((CURRENT_TIME - LAST_ALERT))
        if [ ${DIFF} -lt 3600 ]; then
            log "告警已发送，跳过重复告警（${DIFF}秒前）"
            return
        fi
    fi
    
    # 记录告警时间
    date +%s > "${ALERT_FILE}_${service}"
    
    # 发送企业微信告警（如果配置了）
    # if [ -n "${WECHAT_WEBHOOK}" ]; then
    #     curl -s -X POST ${WECHAT_WEBHOOK} \
    #         -H "Content-Type: application/json" \
    #         -d "{\"msgtype\": \"text\", \"text\": {\"content\": \"🚨 物流获客AI告警\\n服务器: ${SERVER_IP}\\n${message}\"}}"
    # fi
}

# 清除告警状态
clear_alert() {
    local service="$1"
    if [ -f "${ALERT_FILE}_${service}" ]; then
        rm -f "${ALERT_FILE}_${service}"
        log "✅ ${service} 服务已恢复正常"
    fi
}

# 检查Docker容器状态
check_container() {
    local container_name="$1"
    local status=$(docker inspect -f '{{.State.Status}}' ${container_name} 2>/dev/null || echo "not_found")
    
    if [ "${status}" != "running" ]; then
        send_alert "容器 ${container_name} 状态异常: ${status}" "${container_name}"
        return 1
    else
        clear_alert "${container_name}"
        return 0
    fi
}

# 检查HTTP端点
check_http() {
    local url="$1"
    local name="$2"
    local response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 ${url} 2>/dev/null || echo "000")
    
    if [ "${response}" != "200" ]; then
        send_alert "${name} HTTP检查失败: ${url} (状态码: ${response})" "${name}"
        return 1
    else
        clear_alert "${name}"
        return 0
    fi
}

# 检查数据库连接
check_database() {
    local result=$(docker exec logistics-ai-db pg_isready -U admin -d logistics_ai 2>/dev/null || echo "failed")
    
    if [[ "${result}" != *"accepting connections"* ]]; then
        send_alert "PostgreSQL数据库连接异常" "postgres"
        return 1
    else
        clear_alert "postgres"
        return 0
    fi
}

# 检查Redis连接
check_redis() {
    local result=$(docker exec logistics-ai-redis redis-cli ping 2>/dev/null || echo "failed")
    
    if [ "${result}" != "PONG" ]; then
        send_alert "Redis连接异常" "redis"
        return 1
    else
        clear_alert "redis"
        return 0
    fi
}

# 检查磁盘空间
check_disk() {
    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ ${usage} -gt 85 ]; then
        send_alert "磁盘使用率过高: ${usage}%" "disk"
        return 1
    else
        clear_alert "disk"
        return 0
    fi
}

# 检查内存使用
check_memory() {
    local usage=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
    
    if [ ${usage} -gt 90 ]; then
        send_alert "内存使用率过高: ${usage}%" "memory"
        return 1
    else
        clear_alert "memory"
        return 0
    fi
}

# ============================================
# 主检查流程
# ============================================

log "========== 开始健康检查 =========="

FAILED=0

# 检查Docker容器
log "检查Docker容器状态..."
check_container "logistics-ai-db" || ((FAILED++))
check_container "logistics-ai-redis" || ((FAILED++))
check_container "logistics-ai-backend" || ((FAILED++))
check_container "logistics-ai-frontend" || ((FAILED++))
check_container "logistics-ai-nginx" || ((FAILED++))

# 检查数据库和缓存
log "检查数据库和缓存..."
check_database || ((FAILED++))
check_redis || ((FAILED++))

# 检查HTTP服务
log "检查HTTP服务..."
check_http "${NGINX_URL}" "nginx" || ((FAILED++))

# 检查系统资源
log "检查系统资源..."
check_disk || ((FAILED++))
check_memory || ((FAILED++))

# 输出结果
if [ ${FAILED} -eq 0 ]; then
    log "✅ 所有检查通过"
else
    log "⚠️ ${FAILED} 项检查失败"
fi

log "========== 健康检查完成 =========="
