#!/bin/bash

# IP白名单管理脚本
# 用于添加、删除、查看白名单IP

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 白名单配置文件
WHITELIST_FILE="/etc/ssh/whitelist_ips.conf"

# 初始化白名单文件
init_whitelist() {
    if [ ! -f "$WHITELIST_FILE" ]; then
        sudo tee "$WHITELIST_FILE" > /dev/null <<EOF
# SSH白名单IP配置
# 格式：每行一个IP地址或CIDR段
# 示例：
# 192.168.1.100
# 10.0.0.0/24

210.149.115.5
127.0.0.1
EOF
        echo -e "${GREEN}✓ 白名单配置文件已创建：$WHITELIST_FILE${NC}"
    fi
}

# 显示当前白名单
show_whitelist() {
    echo -e "${BLUE}=========================================="
    echo "当前SSH白名单IP列表"
    echo -e "==========================================${NC}"
    
    if [ -f "$WHITELIST_FILE" ]; then
        echo ""
        cat "$WHITELIST_FILE" | grep -v "^#" | grep -v "^$" | nl
        echo ""
    else
        echo -e "${RED}白名单文件不存在${NC}"
    fi
    
    echo -e "${BLUE}=========================================="
    echo "当前防火墙SSH规则"
    echo -e "==========================================${NC}"
    echo ""
    sudo iptables -L INPUT -n --line-numbers | grep "dpt:22"
    echo ""
}

# 添加IP到白名单
add_ip() {
    local ip=$1
    
    if [ -z "$ip" ]; then
        echo -e "${RED}错误：请提供IP地址${NC}"
        echo "用法: $0 add <IP地址>"
        exit 1
    fi
    
    # 验证IP格式
    if ! [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(/[0-9]{1,2})?$ ]]; then
        echo -e "${RED}错误：无效的IP地址格式${NC}"
        exit 1
    fi
    
    # 检查IP是否已存在
    if grep -q "^$ip$" "$WHITELIST_FILE" 2>/dev/null; then
        echo -e "${YELLOW}IP $ip 已在白名单中${NC}"
        exit 0
    fi
    
    # 添加到配置文件
    echo "$ip" | sudo tee -a "$WHITELIST_FILE" > /dev/null
    
    # 添加防火墙规则
    sudo iptables -I INPUT -p tcp --dport 22 -s $ip -j ACCEPT
    
    # 保存规则
    sudo netfilter-persistent save
    
    echo -e "${GREEN}✓ 已添加 $ip 到SSH白名单${NC}"
}

# 从白名单删除IP
remove_ip() {
    local ip=$1
    
    if [ -z "$ip" ]; then
        echo -e "${RED}错误：请提供IP地址${NC}"
        echo "用法: $0 remove <IP地址>"
        exit 1
    fi
    
    # 从配置文件删除
    if [ -f "$WHITELIST_FILE" ]; then
        sudo sed -i "/^$ip$/d" "$WHITELIST_FILE"
    fi
    
    # 删除防火墙规则
    while sudo iptables -D INPUT -p tcp --dport 22 -s $ip -j ACCEPT 2>/dev/null; do
        echo -e "${YELLOW}删除防火墙规则...${NC}"
    done
    
    # 保存规则
    sudo netfilter-persistent save
    
    echo -e "${GREEN}✓ 已从SSH白名单删除 $ip${NC}"
}

# 获取当前公网IP
get_current_ip() {
    echo -e "${BLUE}正在获取当前公网IP...${NC}"
    
    local ip=$(curl -s ifconfig.me)
    
    if [ -z "$ip" ]; then
        ip=$(curl -s icanhazip.com)
    fi
    
    if [ -z "$ip" ]; then
        ip=$(curl -s ipinfo.io/ip)
    fi
    
    if [ -n "$ip" ]; then
        echo -e "${GREEN}当前公网IP: $ip${NC}"
        echo ""
        read -p "是否将此IP添加到白名单？(y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            add_ip "$ip"
        fi
    else
        echo -e "${RED}无法获取公网IP${NC}"
    fi
}

# 应用白名单规则
apply_whitelist() {
    echo -e "${YELLOW}正在应用白名单规则...${NC}"
    
    # 清除现有SSH规则
    sudo iptables -F INPUT
    
    # 允许已建立的连接
    sudo iptables -I INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    
    # 允许本地回环
    sudo iptables -I INPUT -i lo -j ACCEPT
    
    # 读取白名单并添加规则
    while IFS= read -r ip; do
        # 跳过注释和空行
        [[ "$ip" =~ ^#.*$ ]] && continue
        [[ -z "$ip" ]] && continue
        
        sudo iptables -I INPUT -p tcp --dport 22 -s "$ip" -j ACCEPT
        echo -e "${GREEN}✓ 已添加 $ip${NC}"
    done < "$WHITELIST_FILE"
    
    # 添加GitHub Actions IP段
    GITHUB_ACTIONS_IPS=(
        "140.82.112.0/20"
        "143.55.64.0/20"
        "185.199.108.0/22"
        "192.30.252.0/22"
    )
    
    for ip in "${GITHUB_ACTIONS_IPS[@]}"; do
        sudo iptables -I INPUT -p tcp --dport 22 -s $ip -j ACCEPT
        echo -e "${GREEN}✓ 已添加 GitHub Actions $ip${NC}"
    done
    
    # 允许Web服务端口
    sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 9000 -j ACCEPT
    
    # 保护数据库端口
    sudo iptables -I INPUT -p tcp --dport 5432 -s 127.0.0.1 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 33066 -s 127.0.0.1 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 6379 -s 127.0.0.1 -j ACCEPT
    
    # 保护内部服务端口
    sudo iptables -I INPUT -p tcp --dport 3000 -s 127.0.0.1 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 3001 -s 127.0.0.1 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
    
    # 保存规则
    sudo netfilter-persistent save
    
    echo -e "${GREEN}✓ 白名单规则已应用并保存${NC}"
}

# 显示帮助信息
show_help() {
    echo "IP白名单管理工具"
    echo ""
    echo "用法: $0 <命令> [参数]"
    echo ""
    echo "命令:"
    echo "  list              显示当前白名单"
    echo "  add <IP>          添加IP到白名单"
    echo "  remove <IP>       从白名单删除IP"
    echo "  current           获取并添加当前公网IP"
    echo "  apply             应用白名单配置"
    echo "  help              显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 list"
    echo "  $0 add 192.168.1.100"
    echo "  $0 remove 192.168.1.100"
    echo "  $0 current"
    echo ""
}

# 主程序
main() {
    # 检查root权限
    if [ "$EUID" -ne 0 ] && [ "$1" != "help" ]; then
        echo -e "${RED}此脚本需要root权限，请使用sudo运行${NC}"
        exit 1
    fi
    
    # 初始化白名单文件
    if [ "$1" != "help" ]; then
        init_whitelist
    fi
    
    case "$1" in
        list)
            show_whitelist
            ;;
        add)
            add_ip "$2"
            ;;
        remove)
            remove_ip "$2"
            ;;
        current)
            get_current_ip
            ;;
        apply)
            apply_whitelist
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            echo -e "${RED}未知命令: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
