#!/bin/bash

# 服务器安全检查脚本
# 定期检查服务器安全状态

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "腾讯云服务器安全检查"
echo "检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "==========================================${NC}"
echo ""

# 检查项计数
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# 检查函数
check_item() {
    local name=$1
    local status=$2
    local message=$3
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if [ "$status" = "pass" ]; then
        echo -e "${GREEN}✓${NC} $name"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif [ "$status" = "fail" ]; then
        echo -e "${RED}✗${NC} $name"
        echo -e "  ${RED}$message${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    elif [ "$status" = "warn" ]; then
        echo -e "${YELLOW}⚠${NC} $name"
        echo -e "  ${YELLOW}$message${NC}"
        WARNING_CHECKS=$((WARNING_CHECKS + 1))
    fi
}

echo -e "${BLUE}[1] 防火墙检查${NC}"
echo "-------------------------------------------"

# 检查iptables是否运行
if sudo iptables -L >/dev/null 2>&1; then
    check_item "防火墙服务" "pass"
else
    check_item "防火墙服务" "fail" "防火墙未运行"
fi

# 检查SSH端口保护
ssh_rules=$(sudo iptables -L INPUT -n | grep "dpt:22" | wc -l)
if [ "$ssh_rules" -gt 0 ]; then
    check_item "SSH端口保护" "pass"
else
    check_item "SSH端口保护" "warn" "未发现SSH端口保护规则"
fi

# 检查数据库端口保护
postgres_protected=$(sudo iptables -L INPUT -n | grep "dpt:5432" | grep "127.0.0.1" | wc -l)
if [ "$postgres_protected" -gt 0 ]; then
    check_item "PostgreSQL端口保护" "pass"
else
    check_item "PostgreSQL端口保护" "fail" "PostgreSQL端口未受保护"
fi

mysql_protected=$(sudo iptables -L INPUT -n | grep "dpt:33066" | grep "127.0.0.1" | wc -l)
if [ "$mysql_protected" -gt 0 ]; then
    check_item "MySQL端口保护" "pass"
else
    check_item "MySQL端口保护" "fail" "MySQL端口未受保护"
fi

redis_protected=$(sudo iptables -L INPUT -n | grep "dpt:6379" | grep "127.0.0.1" | wc -l)
if [ "$redis_protected" -gt 0 ]; then
    check_item "Redis端口保护" "pass"
else
    check_item "Redis端口保护" "fail" "Redis端口未受保护"
fi

echo ""
echo -e "${BLUE}[2] SSH安全检查${NC}"
echo "-------------------------------------------"

# 检查SSH密码登录
if grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config; then
    check_item "SSH密码登录禁用" "pass"
else
    check_item "SSH密码登录禁用" "fail" "SSH密码登录未禁用"
fi

# 检查root登录
if grep -q "^PermitRootLogin no" /etc/ssh/sshd_config; then
    check_item "Root直接登录禁用" "pass"
else
    check_item "Root直接登录禁用" "warn" "Root可以直接登录"
fi

# 检查SSH密钥
if [ -f "/home/ubuntu/.ssh/authorized_keys" ]; then
    key_count=$(wc -l < /home/ubuntu/.ssh/authorized_keys)
    check_item "SSH密钥配置" "pass"
    echo "  已配置 $key_count 个SSH密钥"
else
    check_item "SSH密钥配置" "warn" "未找到SSH密钥文件"
fi

echo ""
echo -e "${BLUE}[3] Fail2Ban检查${NC}"
echo "-------------------------------------------"

# 检查Fail2Ban服务
if systemctl is-active --quiet fail2ban; then
    check_item "Fail2Ban服务" "pass"
    
    # 显示封禁统计
    banned_count=$(sudo fail2ban-client status sshd 2>/dev/null | grep "Currently banned" | awk '{print $NF}')
    if [ -n "$banned_count" ]; then
        echo "  当前封禁IP数: $banned_count"
    fi
else
    check_item "Fail2Ban服务" "warn" "Fail2Ban未运行"
fi

echo ""
echo -e "${BLUE}[4] 端口开放检查${NC}"
echo "-------------------------------------------"

# 检查对外开放的端口
echo "对外开放的端口："
sudo netstat -tlnp | grep "0.0.0.0" | awk '{print $4, $7}' | while read line; do
    port=$(echo $line | awk -F: '{print $2}' | awk '{print $1}')
    service=$(echo $line | awk '{print $2}')
    
    case $port in
        22)
            echo -e "  ${YELLOW}⚠${NC} 端口 $port (SSH) - $service"
            ;;
        80|443|9000)
            echo -e "  ${GREEN}✓${NC} 端口 $port (Web) - $service"
            ;;
        25)
            echo -e "  ${GREEN}✓${NC} 端口 $port (SMTP) - $service"
            ;;
        *)
            echo -e "  ${RED}✗${NC} 端口 $port - $service (未知服务)"
            ;;
    esac
done

echo ""
echo -e "${BLUE}[5] 系统更新检查${NC}"
echo "-------------------------------------------"

# 检查系统更新
updates=$(apt list --upgradable 2>/dev/null | grep -v "Listing" | wc -l)
if [ "$updates" -eq 0 ]; then
    check_item "系统更新" "pass"
else
    check_item "系统更新" "warn" "有 $updates 个软件包需要更新"
fi

echo ""
echo -e "${BLUE}[6] 日志检查${NC}"
echo "-------------------------------------------"

# 检查最近的SSH登录失败
failed_ssh=$(sudo grep "Failed password" /var/log/auth.log 2>/dev/null | tail -5 | wc -l)
if [ "$failed_ssh" -gt 0 ]; then
    check_item "SSH登录失败记录" "warn" "最近有 $failed_ssh 次SSH登录失败"
    echo "  最近的失败尝试："
    sudo grep "Failed password" /var/log/auth.log 2>/dev/null | tail -3 | while read line; do
        echo "    $line"
    done
else
    check_item "SSH登录失败记录" "pass"
fi

# 检查最近的成功登录
echo ""
echo "最近的成功登录："
last -n 5 | head -5

echo ""
echo -e "${BLUE}[7] 磁盘空间检查${NC}"
echo "-------------------------------------------"

# 检查磁盘使用率
df -h | grep -v "tmpfs" | grep -v "Filesystem" | while read line; do
    usage=$(echo $line | awk '{print $5}' | sed 's/%//')
    mount=$(echo $line | awk '{print $6}')
    
    if [ "$usage" -gt 90 ]; then
        echo -e "${RED}✗${NC} $mount: ${usage}% (严重)"
    elif [ "$usage" -gt 80 ]; then
        echo -e "${YELLOW}⚠${NC} $mount: ${usage}% (警告)"
    else
        echo -e "${GREEN}✓${NC} $mount: ${usage}%"
    fi
done

echo ""
echo -e "${BLUE}[8] 服务运行状态${NC}"
echo "-------------------------------------------"

# 检查关键服务
services=("nginx" "postgresql" "redis-server" "fail2ban")

for service in "${services[@]}"; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        check_item "$service 服务" "pass"
    else
        check_item "$service 服务" "fail" "$service 未运行"
    fi
done

echo ""
echo -e "${BLUE}[9] 网络连接检查${NC}"
echo "-------------------------------------------"

# 检查可疑的网络连接
suspicious_connections=$(sudo netstat -tn | grep ESTABLISHED | grep -v "127.0.0.1" | grep -v "::1" | wc -l)
echo "当前活跃连接数: $suspicious_connections"

# 显示前10个连接最多的IP
echo ""
echo "连接最多的IP地址（前10）："
sudo netstat -tn | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10

echo ""
echo -e "${BLUE}[10] 内存和CPU检查${NC}"
echo "-------------------------------------------"

# 内存使用
mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ "$mem_usage" -gt 90 ]; then
    check_item "内存使用率" "fail" "内存使用率 ${mem_usage}%"
elif [ "$mem_usage" -gt 80 ]; then
    check_item "内存使用率" "warn" "内存使用率 ${mem_usage}%"
else
    check_item "内存使用率" "pass"
    echo "  当前使用率: ${mem_usage}%"
fi

# CPU负载
load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | xargs)
echo "CPU负载平均值: $load_avg"

echo ""
echo -e "${BLUE}=========================================="
echo "检查摘要"
echo -e "==========================================${NC}"
echo -e "总检查项: $TOTAL_CHECKS"
echo -e "${GREEN}通过: $PASSED_CHECKS${NC}"
echo -e "${YELLOW}警告: $WARNING_CHECKS${NC}"
echo -e "${RED}失败: $FAILED_CHECKS${NC}"
echo ""

if [ "$FAILED_CHECKS" -gt 0 ]; then
    echo -e "${RED}发现安全问题，请立即处理！${NC}"
    exit 1
elif [ "$WARNING_CHECKS" -gt 0 ]; then
    echo -e "${YELLOW}发现警告项，建议检查${NC}"
    exit 0
else
    echo -e "${GREEN}安全检查全部通过！${NC}"
    exit 0
fi
