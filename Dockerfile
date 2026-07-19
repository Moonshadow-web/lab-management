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

# 数据目录（CloudBase Run 挂载持久卷到此路径 /app/data）
# 注意：绝不能在构建期在 /app/data 下预建目录（如 /app/data/uploads），
# 否则镜像里 mountPath 目录已含内容，会与 CFS 持久卷挂载冲突（腾讯云报错
# “/app/data/upload 与挂载路径冲突”）。相关子目录改在 entrypoint 运行时、
# 卷已挂载后再创建（见下方启动脚本）。
ENV DATA_DIR=/app/data
ENV UPLOAD_ROOT=/app/data/uploads
ENV SECRET_KEY=923fc5168b97f6cde072ae078aac3db8ce4cbef562ecb623523a8e34bd9bc78b

# 启动脚本：首次运行时从备份恢复数据到持久卷
# 注意：/app/data 是 CFS 持久卷挂载点，必须在运行时（卷已挂载）才创建子目录，
# 不能在 Dockerfile 构建期预建，否则会与挂载冲突。
RUN echo '#!/bin/sh\n# 运行时在已挂载的持久卷上创建子目录（构建期不得预建，避免与挂载冲突）\nmkdir -p /app/data/uploads /app/data/eqa_reports\nif [ ! -f /app/data/app.db ]; then\n  echo "First run: restoring database from backup..."\n  cp /app/backup/app.db /app/data/app.db\nfi\nif [ -d /app/backup/uploads ] && [ -z "$(ls -A /app/data/uploads 2>/dev/null)" ]; then\n  echo "First run: restoring uploads from backup..."\n  cp -r /app/backup/uploads/* /app/data/uploads/ 2>/dev/null || true\nfi\nif [ -d /app/backup/eqa_reports ]; then\n  echo "Syncing EQA reports from image (authoritative)..."\n  cp -r /app/backup/eqa_reports/* /app/data/eqa_reports/ 2>/dev/null || true\nfi\nexec uvicorn app.main:app --host 0.0.0.0 --port 8080' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# 暴露端口（CloudBase Run 要求）
EXPOSE 8080

# 启动
CMD ["/app/entrypoint.sh"]
