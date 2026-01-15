#!/bin/bash
# =============================================================================
# 原生部署安装脚本
# 在腾讯云 CVM 上安装所有必要的服务组件
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
PROJECT_DIR="/home/ubuntu/logistics-ai"
PYTHON_VERSION="3.11"
NODE_VERSION="20"
PG_VERSION="15"
REDIS_VERSION="7"

echo -e "${BLUE}"
echo "=============================================="
echo "    物流获客AI - 原生部署安装脚本"
echo "=============================================="
echo -e "${NC}"

# -----------------------------------------------------------------------------
# 检查是否为 root 或有 sudo 权限
# -----------------------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
    if ! sudo -n true 2>/dev/null; then
        echo -e "${RED}请使用 sudo 运行此脚本${NC}"
        exit 1
    fi
    SUDO="sudo"
else
    SUDO=""
fi

# -----------------------------------------------------------------------------
# 1. 系统更新
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[1/8] 更新系统包...${NC}"
$SUDO apt update && $SUDO apt upgrade -y
echo -e "${GREEN}✓ 系统更新完成${NC}"

# -----------------------------------------------------------------------------
# 2. 安装 PostgreSQL 15
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/8] 安装 PostgreSQL ${PG_VERSION}...${NC}"

# 添加 PostgreSQL 官方仓库
$SUDO apt install -y curl ca-certificates gnupg
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | $SUDO gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | $SUDO tee /etc/apt/sources.list.d/pgdg.list

$SUDO apt update
$SUDO apt install -y postgresql-${PG_VERSION} postgresql-contrib-${PG_VERSION}

# 启动并设置开机自启
$SUDO systemctl start postgresql
$SUDO systemctl enable postgresql

echo -e "${GREEN}✓ PostgreSQL ${PG_VERSION} 安装完成${NC}"

# -----------------------------------------------------------------------------
# 3. 配置 PostgreSQL
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/8] 配置 PostgreSQL...${NC}"

# 从 .env 文件读取配置（如果存在）
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

DB_USER="${POSTGRES_USER:-admin}"
DB_PASSWORD="${POSTGRES_PASSWORD:-your_secure_password_here}"
DB_NAME="${POSTGRES_DB:-logistics_ai}"

# 创建数据库用户和数据库
$SUDO -u postgres psql <<EOF
-- 创建用户（如果不存在）
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
        CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END
\$\$;

-- 创建数据库（如果不存在）
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}' 
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec

-- 授权
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
ALTER USER ${DB_USER} WITH SUPERUSER;
EOF

# 配置 pg_hba.conf 允许本地密码认证
PG_HBA="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"
if ! grep -q "host.*${DB_NAME}.*${DB_USER}" "$PG_HBA"; then
    echo "host    ${DB_NAME}    ${DB_USER}    127.0.0.1/32    scram-sha-256" | $SUDO tee -a "$PG_HBA"
fi

# 重启 PostgreSQL 应用配置
$SUDO systemctl restart postgresql

echo -e "${GREEN}✓ PostgreSQL 配置完成${NC}"
echo "  数据库: ${DB_NAME}"
echo "  用户: ${DB_USER}"

# -----------------------------------------------------------------------------
# 4. 安装 Redis 7
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/8] 安装 Redis ${REDIS_VERSION}...${NC}"

# 添加 Redis 官方仓库
curl -fsSL https://packages.redis.io/gpg | $SUDO gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | $SUDO tee /etc/apt/sources.list.d/redis.list

$SUDO apt update
$SUDO apt install -y redis

# 配置 Redis
$SUDO sed -i 's/^# maxmemory .*/maxmemory 256mb/' /etc/redis/redis.conf
$SUDO sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
$SUDO sed -i 's/^appendonly no/appendonly yes/' /etc/redis/redis.conf

# 启动并设置开机自启
$SUDO systemctl start redis-server
$SUDO systemctl enable redis-server

echo -e "${GREEN}✓ Redis ${REDIS_VERSION} 安装完成${NC}"

# -----------------------------------------------------------------------------
# 5. 安装 Python 3.11
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[5/8] 安装 Python ${PYTHON_VERSION}...${NC}"

$SUDO apt install -y software-properties-common
$SUDO add-apt-repository -y ppa:deadsnakes/ppa
$SUDO apt update
$SUDO apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev

# 安装系统依赖（视频处理等）
$SUDO apt install -y ffmpeg fonts-wqy-zenhei fonts-wqy-microhei imagemagick libpq-dev gcc

echo -e "${GREEN}✓ Python ${PYTHON_VERSION} 安装完成${NC}"

# -----------------------------------------------------------------------------
# 6. 配置 Python 虚拟环境和后端
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[6/8] 配置后端 Python 环境...${NC}"

# 创建虚拟环境
cd "$PROJECT_DIR/backend"
python${PYTHON_VERSION} -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 安装 Gunicorn（生产级 WSGI 服务器）
pip install gunicorn uvloop httptools

deactivate

echo -e "${GREEN}✓ 后端 Python 环境配置完成${NC}"

# -----------------------------------------------------------------------------
# 7. 安装 Node.js 和配置前端
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[7/8] 安装 Node.js ${NODE_VERSION} 并配置前端...${NC}"

# 使用 NodeSource 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | $SUDO bash -
$SUDO apt install -y nodejs

# 安装 PM2
$SUDO npm install -g pm2

# 构建前端
cd "$PROJECT_DIR/frontend"
npm ci --legacy-peer-deps
npm run build

echo -e "${GREEN}✓ Node.js 和前端配置完成${NC}"

# -----------------------------------------------------------------------------
# 8. 安装和配置 Nginx
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[8/8] 安装 Nginx...${NC}"

$SUDO apt install -y nginx

# 复制 Nginx 配置
$SUDO cp "$PROJECT_DIR/scripts/native-deploy/nginx-native.conf" /etc/nginx/nginx.conf

# 测试配置
$SUDO nginx -t

# 启动并设置开机自启
$SUDO systemctl start nginx
$SUDO systemctl enable nginx

echo -e "${GREEN}✓ Nginx 安装完成${NC}"

# -----------------------------------------------------------------------------
# 完成
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}"
echo "=============================================="
echo "    安装完成！"
echo "=============================================="
echo -e "${NC}"
echo ""
echo -e "${GREEN}已安装的组件:${NC}"
echo "  ✓ PostgreSQL ${PG_VERSION}"
echo "  ✓ Redis ${REDIS_VERSION}"
echo "  ✓ Python ${PYTHON_VERSION}"
echo "  ✓ Node.js ${NODE_VERSION}"
echo "  ✓ Nginx"
echo "  ✓ PM2"
echo ""
echo -e "${YELLOW}下一步:${NC}"
echo "1. 恢复数据库备份（如果有）:"
echo "   sudo -u postgres pg_restore -d ${DB_NAME} /path/to/postgres_backup.dump"
echo ""
echo "2. 安装 systemd 服务:"
echo "   sudo cp $PROJECT_DIR/scripts/native-deploy/logistics-backend.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable logistics-backend"
echo "   sudo systemctl start logistics-backend"
echo ""
echo "3. 启动前端:"
echo "   cd $PROJECT_DIR/frontend && pm2 start ecosystem.config.js"
echo "   pm2 save"
echo "   pm2 startup"
echo ""
echo "4. 重启 Nginx:"
echo "   sudo systemctl restart nginx"
echo ""
