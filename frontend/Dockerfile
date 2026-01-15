# 优化的多阶段构建 - 利用 Docker 层缓存加速构建
FROM node:20-alpine AS base

# 配置淘宝npm镜像
RUN npm config set registry https://registry.npmmirror.com

# ============ 安装依赖阶段 ============
# 这一层只在 package.json 变化时才重新构建
FROM base AS deps
WORKDIR /app

# 先只复制 package.json 和 lock 文件
# 这样只有依赖变化时才会重新 npm install
COPY package.json package-lock.json* ./

# 使用 npm ci 更快（如果有 lock 文件）
RUN if [ -f package-lock.json ]; then \
      npm ci --legacy-peer-deps --registry https://registry.npmmirror.com; \
    else \
      npm install --legacy-peer-deps --registry https://registry.npmmirror.com; \
    fi

# ============ 构建阶段 ============
FROM base AS builder
WORKDIR /app

# 复制依赖
COPY --from=deps /app/node_modules ./node_modules

# 复制源代码
COPY . .

# 设置构建时环境变量
ENV NEXT_TELEMETRY_DISABLED 1
ENV NODE_ENV production

# 构建
RUN npm run build

# ============ 生产镜像 ============
FROM base AS runner
WORKDIR /app
ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# 安装curl用于健康检查
RUN apk add --no-cache curl

# 创建非root用户
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# 只复制必要的文件
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT 3000
ENV HOSTNAME 0.0.0.0

CMD ["node", "server.js"]
