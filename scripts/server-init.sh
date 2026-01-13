#!/bin/bash
# ============================================================
# 物流获客AI - 腾讯云 CVM 服务器初始化脚本
# 首次部署时在服务器上运行此脚本
# 使用方法: sudo bash server-init.sh
# ============================================================

set -e

echo "=============================================="
echo "🚀 物流获客AI - 服务器初始化脚本"
echo "=============================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ 请使用 root 权限运行此脚本${NC}"
  echo "使用方法: sudo bash server-init.sh"
  exit 1
fi

echo -e "${GREEN}✅ Root 权限检查通过${NC}"

# ==================== 1. 系统更新 ====================
echo ""
echo -e "${YELLOW}📦 [1/6] 更新系统包...${NC}"
apt-get update -y
apt-get upgrade -y

# ==================== 2. 安装必要工具 ====================
echo ""
echo -e "${YELLOW}🔧 [2/6] 安装必要工具...${NC}"
apt-get install -y \
  curl \
  wget \
  git \
  vim \
  htop \
  unzip \
  ca-certificates \
  gnupg \
  lsb-release \
  ufw

# ==================== 3. 安装 Docker ====================
echo ""
echo -e "${YELLOW}🐳 [3/6] 安装 Docker...${NC}"

# 检查 Docker 是否已安装
if command -v docker &> /dev/null; then
  echo -e "${GREEN}✅ Docker 已安装，跳过...${NC}"
  docker --version
else
  # 安装 Docker
  curl -fsSL https://get.docker.com -o get-docker.sh
  sh get-docker.sh
  rm get-docker.sh
  
  # 启动 Docker 服务
  systemctl start docker
  systemctl enable docker
  
  echo -e "${GREEN}✅ Docker 安装完成${NC}"
  docker --version
fi

# ==================== 4. 安装 Docker Compose ====================
echo ""
echo -e "${YELLOW}🐳 [4/6] 检查 Docker Compose...${NC}"

if docker compose version &> /dev/null; then
  echo -e "${GREEN}✅ Docker Compose 已安装${NC}"
  docker compose version
else
  echo -e "${YELLOW}安装 Docker Compose 插件...${NC}"
  apt-get install -y docker-compose-plugin
  echo -e "${GREEN}✅ Docker Compose 安装完成${NC}"
  docker compose version
fi

# ==================== 5. 创建部署用户 ====================
echo ""
echo -e "${YELLOW}👤 [5/6] 配置部署用户...${NC}"

DEPLOY_USER="deploy"
DEPLOY_PATH="/home/$DEPLOY_USER/logistics-ai"

# 创建部署用户（如果不存在）
if id "$DEPLOY_USER" &>/dev/null; then
  echo -e "${GREEN}✅ 用户 $DEPLOY_USER 已存在${NC}"
else
  useradd -m -s /bin/bash $DEPLOY_USER
  echo -e "${GREEN}✅ 创建用户 $DEPLOY_USER${NC}"
fi

# 将用户添加到 docker 组
usermod -aG docker $DEPLOY_USER
echo -e "${GREEN}✅ 已将 $DEPLOY_USER 添加到 docker 组${NC}"

# 创建部署目录
mkdir -p $DEPLOY_PATH
chown -R $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER
echo -e "${GREEN}✅ 创建部署目录: $DEPLOY_PATH${NC}"

# ==================== 6. 配置防火墙 ====================
echo ""
echo -e "${YELLOW}🔥 [6/6] 配置防火墙...${NC}"

# 启用 UFW
ufw --force enable

# 允许 SSH
ufw allow 22/tcp

# 允许 HTTP 和 HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# 显示防火墙状态
ufw status

echo -e "${GREEN}✅ 防火墙配置完成${NC}"

# ==================== 完成 ====================
echo ""
echo "=============================================="
echo -e "${GREEN}🎉 服务器初始化完成!${NC}"
echo "=============================================="
echo ""
echo "📋 下一步操作："
echo ""
echo "1️⃣  配置 SSH 密钥（用于 GitHub Actions 自动部署）"
echo "    在本地生成密钥对:"
echo "    ssh-keygen -t ed25519 -C 'github-actions-deploy'"
echo ""
echo "    将公钥添加到服务器:"
echo "    ssh-copy-id -i ~/.ssh/id_ed25519.pub $DEPLOY_USER@<服务器IP>"
echo ""
echo "2️⃣  在 GitHub 仓库设置 Secrets（Settings -> Secrets and variables -> Actions）"
echo "    必需的 Secrets:"
echo "    - SERVER_HOST: 服务器IP地址"
echo "    - SERVER_USER: $DEPLOY_USER"
echo "    - SERVER_SSH_KEY: SSH 私钥内容"
echo "    - POSTGRES_USER: 数据库用户名"
echo "    - POSTGRES_PASSWORD: 数据库密码（请使用强密码）"
echo "    - POSTGRES_DB: logistics_ai"
echo "    - JWT_SECRET: JWT密钥（随机字符串）"
echo ""
echo "3️⃣  可选的 Secrets（根据需要配置）:"
echo "    - DASHSCOPE_API_KEY: 通义千问API密钥"
echo "    - OPENAI_API_KEY: OpenAI API密钥"
echo "    - KELING_API_KEY: 可灵视频API密钥"
echo "    - WECHAT_CORP_ID: 企业微信企业ID"
echo "    - WECHAT_AGENT_ID: 企业微信应用ID"
echo "    - WECHAT_SECRET: 企业微信Secret"
echo ""
echo "4️⃣  推送代码到 GitHub main 分支，自动触发部署"
echo ""
echo "=============================================="
