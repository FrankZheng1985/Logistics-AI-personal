FROM python:3.11-slim-bookworm

WORKDIR /app

# 使用腾讯云内网镜像源
RUN echo "deb http://mirrors.tencentyun.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirrors.tencentyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.tencentyun.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装系统依赖（包含视频处理所需的 FFmpeg 和中文字体）
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    # 视频处理依赖
    ffmpeg \
    # 中文字体（用于视频字幕渲染）
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-noto-cjk \
    # ImageMagick（moviepy TextClip 需要）
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# 配置 ImageMagick 策略（允许 PDF 和文字渲染）
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true

# 复制依赖文件
COPY requirements.txt .

# 使用腾讯云pip镜像安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i http://mirrors.tencentyun.com/pypi/simple --trusted-host mirrors.tencentyun.com

# 复制应用代码
COPY . .

# 创建视频输出临时目录
RUN mkdir -p /tmp/video_output

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
