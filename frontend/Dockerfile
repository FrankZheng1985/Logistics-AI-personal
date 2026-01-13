FROM node:20-alpine AS base

# 配置淘宝npm镜像
RUN npm config set registry https://registry.npmmirror.com

# 安装依赖
FROM base AS deps
WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps --registry https://registry.npmmirror.com

# 构建
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# 生产镜像
FROM base AS runner
WORKDIR /app
ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT 3000

CMD ["node", "server.js"]
