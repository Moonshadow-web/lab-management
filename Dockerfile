# ====== Stage 1: 构建前端 ======
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --production=false
COPY frontend/ ./
RUN npm run build

# ====== Stage 2: 运行后端 + 托管前端 ======
FROM python:3.13-slim
WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码
COPY backend/ ./

# 前端构建产物（main.py 在生产模式 serve 它）
COPY --from=frontend-builder /build/dist ./frontend/dist

# 初始数据备份（首次启动复制到持久卷，不覆盖已有数据）
COPY data/app.db /app/backup/app.db
COPY data/uploads /app/backup/uploads
# EQA 质评报告 PDF 备份（首次/空目录时恢复到持久卷，避免线上预览 404）
COPY data/eqa_reports /app/backup/eqa_reports

# 数据目录（CloudBase Run 挂载持久卷到此路径）
RUN mkdir -p /app/data/uploads
ENV DATA_DIR=/app/data
ENV UPLOAD_ROOT=/app/data/uploads
ENV SECRET_KEY=923fc5168b97f6cde072ae078aac3db8ce4cbef562ecb623523a8e34bd9bc78b

# 启动脚本：首次运行时从备份恢复数据到持久卷
RUN echo '#!/bin/sh\nif [ ! -f /app/data/app.db ]; then\n  echo "First run: restoring database from backup..."\n  cp /app/backup/app.db /app/data/app.db\nfi\nif [ -d /app/backup/uploads ] && [ -z "$(ls -A /app/data/uploads 2>/dev/null)" ]; then\n  echo "First run: restoring uploads from backup..."\n  cp -r /app/backup/uploads/* /app/data/uploads/ 2>/dev/null || true\nfi\nif [ -d /app/backup/eqa_reports ]; then\n  echo "Syncing EQA reports from image (authoritative)..."\n  mkdir -p /app/data/eqa_reports\n  cp -r /app/backup/eqa_reports/* /app/data/eqa_reports/ 2>/dev/null || true\nfi\nexec uvicorn app.main:app --host 0.0.0.0 --port 8080' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# 暴露端口（CloudBase Run 要求）
EXPOSE 8080

# 启动
CMD ["/app/entrypoint.sh"]
