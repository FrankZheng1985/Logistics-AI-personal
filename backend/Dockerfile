# 优化的后端 Dockerfile - 利用 Docker 层缓存
FROM python:3.11-slim-bookworm

WORKDIR /app

# ============ 系统依赖层（很少变化，可长期缓存）============
# 使用腾讯云内网镜像源
RUN echo "deb http://mirrors.tencentyun.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirrors.tencentyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.tencentyun.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装系统依赖（包含视频处理所需的 FFmpeg 和中文字体）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    ffmpeg \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-noto-cjk \
    imagemagick \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 配置 ImageMagick 策略
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true

# ============ Python 依赖层（只在 requirements.txt 变化时重建）============
# 先只复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt \
    -i http://mirrors.tencentyun.com/pypi/simple \
    --trusted-host mirrors.tencentyun.com

# 安装 Playwright 浏览器（用于社交媒体采集）
# 注意：这会增加镜像大小约 400MB
RUN playwright install chromium --with-deps || true

# ============ 应用代码层（每次代码变化都会重建）============
COPY . .

# 创建视频输出临时目录
RUN mkdir -p /tmp/video_output

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
