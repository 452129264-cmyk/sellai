# SellAI v3.0.0 Dockerfile
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src ./src
COPY avatar_independent ./avatar_independent
COPY voice_system ./voice_system
COPY main.py .
COPY data ./data
COPY docs ./docs
COPY .env .

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 8000

# 健康检查 - 增加等待时间解决启动慢导致502问题
# v3.2.0修复版：等待时间从5s增加到120s
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "main.py"]
# build v3.6.1
