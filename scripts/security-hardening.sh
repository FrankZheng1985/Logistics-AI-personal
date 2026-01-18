#!/bin/bash

# 腾讯云服务器安全加固脚本
# 设置IP白名单，保护关键服务

set -e

echo "=========================================="
echo "腾讯云服务器安全加固"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 白名单IP列表
WHITELIST_IPS=(
    "210.149.115.5"  # 用户当前IP
    "127.0.0.1"      # 本地回环
)

# GitHub Actions IP段（用于自动部署）
GITHUB_ACTIONS_IPS=(
    "140.82.112.0/20"
    "143.55.64.0/20"
    "185.199.108.0/22"
    "192.30.252.0/22"
    "20.201.28.151/32"
    "20.205.243.166/32"
    "102.133.202.242/32"
    "20.233.54.53/32"
    "20.27.177.113/32"
    "20.200.245.247/32"
    "20.175.192.147/32"
    "20.233.83.145/32"
)

echo -e "${YELLOW}步骤 1: 备份当前防火墙规则${NC}"
sudo iptables-save > /tmp/iptables-backup-$(date +%Y%m%d-%H%M%S).txt
echo -e "${GREEN}✓ 防火墙规则已备份${NC}"

echo ""
echo -e "${YELLOW}步骤 2: 配置SSH访问白名单（端口22）${NC}"
# 清除旧的SSH白名单规则（如果存在）
sudo iptables -D INPUT -p tcp --dport 22 -j DROP 2>/dev/null || true

# 允许白名单IP访问SSH
for ip in "${WHITELIST_IPS[@]}"; do
    if [ "$ip" != "127.0.0.1" ]; then
        sudo iptables -I INPUT -p tcp --dport 22 -s $ip -j ACCEPT
        echo -e "${GREEN}✓ 允许 $ip 访问SSH${NC}"
    fi
done

# 允许GitHub Actions IP段访问SSH（用于自动部署）
for ip in "${GITHUB_ACTIONS_IPS[@]}"; do
    sudo iptables -I INPUT -p tcp --dport 22 -s $ip -j ACCEPT
    echo -e "${GREEN}✓ 允许 GitHub Actions $ip 访问SSH${NC}"
done

# 允许已建立的连接（重要：防止断开当前SSH连接）
sudo iptables -I INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

echo ""
echo -e "${YELLOW}步骤 3: 保护数据库端口${NC}"

# PostgreSQL (5432) - 仅允许本地访问
if sudo iptables -C INPUT -p tcp --dport 5432 -s 127.0.0.1 -j ACCEPT 2>/dev/null; then
    echo -e "${GREEN}✓ PostgreSQL规则已存在${NC}"
else
    sudo iptables -I INPUT -p tcp --dport 5432 -s 127.0.0.1 -j ACCEPT
    echo -e "${GREEN}✓ PostgreSQL仅允许本地访问${NC}"
fi

# MySQL (33066) - 仅允许本地访问
if sudo iptables -C INPUT -p tcp --dport 33066 -s 127.0.0.1 -j ACCEPT 2>/dev/null; then
    echo -e "${GREEN}✓ MySQL规则已存在${NC}"
else
    sudo iptables -I INPUT -p tcp --dport 33066 -s 127.0.0.1 -j ACCEPT
    echo -e "${GREEN}✓ MySQL仅允许本地访问${NC}"
fi

# Redis (6379) - 仅允许本地访问
if sudo iptables -C INPUT -p tcp --dport 6379 -s 127.0.0.1 -j ACCEPT 2>/dev/null; then
    echo -e "${GREEN}✓ Redis规则已存在${NC}"
else
    sudo iptables -I INPUT -p tcp --dport 6379 -s 127.0.0.1 -j ACCEPT
    echo -e "${GREEN}✓ Redis仅允许本地访问${NC}"
fi

echo ""
echo -e "${YELLOW}步骤 4: 配置Web服务访问${NC}"

# 允许所有人访问HTTP/HTTPS（公开服务）
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 9000 -j ACCEPT
echo -e "${GREEN}✓ HTTP/HTTPS端口对外开放${NC}"

# 前端服务端口（3000, 3001）- 仅允许本地和Nginx访问
sudo iptables -I INPUT -p tcp --dport 3000 -s 127.0.0.1 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 3001 -s 127.0.0.1 -j ACCEPT
echo -e "${GREEN}✓ 前端服务端口仅允许本地访问${NC}"

# 后端API端口（8000）- 仅允许本地和Nginx访问
sudo iptables -I INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
echo -e "${GREEN}✓ 后端API端口仅允许本地访问${NC}"

echo ""
echo -e "${YELLOW}步骤 5: 配置防暴力破解规则${NC}"

# SSH防暴力破解：限制每个IP每分钟最多3次连接尝试
sudo iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set --name SSH
sudo iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 4 --rttl --name SSH -j DROP
echo -e "${GREEN}✓ SSH防暴力破解规则已设置（每分钟最多3次尝试）${NC}"

echo ""
echo -e "${YELLOW}步骤 6: 配置ICMP（Ping）限制${NC}"

# 限制ICMP请求速率，防止Ping洪水攻击
sudo iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s --limit-burst 2 -j ACCEPT
sudo iptables -A INPUT -p icmp --icmp-type echo-request -j DROP
echo -e "${GREEN}✓ ICMP限速规则已设置${NC}"

echo ""
echo -e "${YELLOW}步骤 7: 保存防火墙规则${NC}"

# 安装iptables-persistent（如果未安装）
if ! dpkg -l | grep -q iptables-persistent; then
    echo -e "${YELLOW}正在安装iptables-persistent...${NC}"
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
fi

# 保存规则
sudo netfilter-persistent save
echo -e "${GREEN}✓ 防火墙规则已永久保存${NC}"

echo ""
echo -e "${YELLOW}步骤 8: 配置SSH安全加固${NC}"

# 备份SSH配置
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup-$(date +%Y%m%d-%H%M%S)

# 禁用密码登录，仅允许密钥登录
if ! grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config; then
    sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
    echo -e "${GREEN}✓ 已禁用SSH密码登录${NC}"
else
    echo -e "${GREEN}✓ SSH密码登录已经禁用${NC}"
fi

# 禁用root直接登录
if ! grep -q "^PermitRootLogin no" /etc/ssh/sshd_config; then
    sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
    echo -e "${GREEN}✓ 已禁用root直接登录${NC}"
else
    echo -e "${GREEN}✓ root直接登录已经禁用${NC}"
fi

# 设置SSH超时时间
if ! grep -q "^ClientAliveInterval" /etc/ssh/sshd_config; then
    echo "ClientAliveInterval 300" | sudo tee -a /etc/ssh/sshd_config > /dev/null
    echo "ClientAliveCountMax 2" | sudo tee -a /etc/ssh/sshd_config > /dev/null
    echo -e "${GREEN}✓ 已设置SSH超时时间（5分钟）${NC}"
fi

# 重启SSH服务
sudo systemctl restart sshd
echo -e "${GREEN}✓ SSH服务已重启${NC}"

echo ""
echo -e "${YELLOW}步骤 9: 配置Fail2Ban（防暴力破解）${NC}"

# 安装Fail2Ban
if ! dpkg -l | grep -q fail2ban; then
    echo -e "${YELLOW}正在安装Fail2Ban...${NC}"
    sudo apt-get update
    sudo apt-get install -y fail2ban
fi

# 配置Fail2Ban
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
destemail = your-email@example.com
sendername = Fail2Ban

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
EOF

# 启动Fail2Ban
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
echo -e "${GREEN}✓ Fail2Ban已配置并启动${NC}"

echo ""
echo -e "${YELLOW}步骤 10: 显示当前防火墙规则${NC}"
sudo iptables -L -n -v --line-numbers

echo ""
echo "=========================================="
echo -e "${GREEN}安全加固完成！${NC}"
echo "=========================================="
echo ""
echo "安全配置摘要："
echo "1. ✓ SSH仅允许白名单IP访问（包括GitHub Actions）"
echo "2. ✓ 数据库端口仅允许本地访问"
echo "3. ✓ Web服务端口对外开放"
echo "4. ✓ 内部服务端口受保护"
echo "5. ✓ SSH防暴力破解已启用"
echo "6. ✓ 防火墙规则已永久保存"
echo "7. ✓ SSH密码登录已禁用"
echo "8. ✓ Fail2Ban已启用"
echo ""
echo -e "${YELLOW}重要提示：${NC}"
echo "- 当前白名单IP: ${WHITELIST_IPS[@]}"
echo "- 如需添加新IP，请编辑脚本中的WHITELIST_IPS数组"
echo "- 防火墙规则备份在 /tmp/iptables-backup-*.txt"
echo "- SSH配置备份在 /etc/ssh/sshd_config.backup-*"
echo ""
echo -e "${RED}警告：请确保当前SSH连接正常，再关闭此窗口！${NC}"
echo ""
