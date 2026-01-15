# 原生部署指南

本目录包含将物流获客AI从 Docker 容器迁移到原生部署的所有脚本。

## 架构对比

| 组件 | Docker 部署 | 原生部署 |
|------|-------------|----------|
| PostgreSQL | 容器 | 系统服务 (systemd) |
| Redis | 容器 | 系统服务 (systemd) |
| 后端 | 容器 + Uvicorn | Gunicorn + systemd |
| 前端 | 容器 + Node | PM2 进程管理 |
| Nginx | 容器 | 系统服务 (systemd) |

## 迁移步骤

### 第一步：备份 Docker 数据

```bash
# 连接服务器
ssh -i /Users/fengzheng/Downloads/Cursor.pem ubuntu@81.70.239.82

# 进入项目目录
cd /home/ubuntu/logistics-ai

# 运行备份脚本
chmod +x scripts/native-deploy/backup-docker.sh
./scripts/native-deploy/backup-docker.sh
```

### 第二步：停止 Docker 容器

```bash
# 停止所有容器
docker-compose -f docker-compose.prod.yml down

# 确认容器已停止
docker ps
```

### 第三步：安装原生服务

```bash
# 运行安装脚本
chmod +x scripts/native-deploy/install.sh
sudo ./scripts/native-deploy/install.sh
```

### 第四步：恢复数据

```bash
# 恢复 PostgreSQL 和 Redis 数据
chmod +x scripts/native-deploy/restore-data.sh
./scripts/native-deploy/restore-data.sh /home/ubuntu/backups/docker-migration-XXXXXXXX
```

### 第五步：安装服务配置

```bash
# 复制 systemd 服务文件
sudo cp scripts/native-deploy/logistics-backend.service /etc/systemd/system/

# 重载 systemd
sudo systemctl daemon-reload

# 复制 Nginx 配置
sudo cp scripts/native-deploy/nginx-native.conf /etc/nginx/nginx.conf
sudo nginx -t

# 复制 PM2 配置
cp scripts/native-deploy/ecosystem.config.js frontend/
```

### 第六步：启动所有服务

```bash
# 运行启动脚本
chmod +x scripts/native-deploy/start-services.sh
./scripts/native-deploy/start-services.sh
```

### 第七步：配置健康检查

```bash
# 设置定时健康检查（每5分钟）
chmod +x scripts/native-deploy/healthcheck.sh
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/ubuntu/logistics-ai/scripts/native-deploy/healthcheck.sh") | crontab -
```

### 第八步：配置 PM2 开机自启

```bash
# 保存 PM2 进程列表
pm2 save

# 设置开机启动
pm2 startup
# 按照输出的命令执行
```

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `backup-docker.sh` | 备份 Docker 容器中的数据 |
| `install.sh` | 安装所有原生服务 |
| `restore-data.sh` | 从备份恢复数据 |
| `start-services.sh` | 启动所有服务 |
| `stop-services.sh` | 停止所有服务 |
| `healthcheck.sh` | 健康检查和自动恢复 |

## 配置文件说明

| 文件 | 用途 |
|------|------|
| `logistics-backend.service` | 后端 systemd 服务配置 |
| `ecosystem.config.js` | PM2 前端进程配置 |
| `nginx-native.conf` | Nginx 反向代理配置 |

## 常用管理命令

### 查看服务状态

```bash
# 查看所有服务状态
sudo systemctl status postgresql redis-server logistics-backend nginx

# 查看 PM2 进程
pm2 list
```

### 查看日志

```bash
# 后端日志
sudo journalctl -u logistics-backend -f

# 前端日志
pm2 logs logistics-frontend

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# PostgreSQL 日志
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### 重启服务

```bash
# 重启后端
sudo systemctl restart logistics-backend

# 重启前端
pm2 reload logistics-frontend

# 重启 Nginx
sudo systemctl restart nginx
```

### 数据库管理

```bash
# 连接数据库
sudo -u postgres psql -d logistics_ai

# 手动备份
sudo -u postgres pg_dump logistics_ai > backup.sql
```

## 回滚到 Docker

如果需要回滚到 Docker 部署：

```bash
# 停止原生服务
./scripts/native-deploy/stop-services.sh

# 禁用 systemd 服务
sudo systemctl disable logistics-backend postgresql redis-server

# 启动 Docker
cd /home/ubuntu/logistics-ai
docker-compose -f docker-compose.prod.yml up -d
```

## 故障排查

### 后端无法启动

1. 检查日志：`sudo journalctl -u logistics-backend -n 100`
2. 检查 Python 环境：`source backend/venv/bin/activate && python -c "import app.main"`
3. 检查数据库连接：`psql -h 127.0.0.1 -U admin -d logistics_ai`

### 前端无法访问

1. 检查 PM2 状态：`pm2 list`
2. 检查日志：`pm2 logs logistics-frontend`
3. 检查端口：`netstat -tlnp | grep 3000`

### Nginx 502 错误

1. 检查后端是否运行：`curl http://127.0.0.1:8000/health`
2. 检查前端是否运行：`curl http://127.0.0.1:3000`
3. 检查 Nginx 日志：`sudo tail -f /var/log/nginx/error.log`
