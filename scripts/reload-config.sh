#!/usr/bin/env bash
# ============================================================
# reload-config.sh — 更新配置并重启 backend
# 用法: 编辑 config/.env 后运行 ./scripts/reload-config.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

if [ ! -f config/.env ]; then
    echo "❌ config/.env 不存在"
    exit 1
fi

# Source config for docker-compose variable substitution
set -a; source config/.env; set +a

echo "正在重启 backend 以加载新配置..."

# Recreate backend container with new env (DB data preserved)
$COMPOSE up -d --force-recreate backend

echo ""
echo "等待 backend 就绪..."
ATTEMPTS=0
MAX_ATTEMPTS=20
while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    if curl -sf http://localhost:80/health > /dev/null 2>&1; then
        echo "[OK] 配置已更新，服务就绪"
        exit 0
    fi
    ATTEMPTS=$((ATTEMPTS + 1))
    sleep 3
done

echo "⚠ 服务启动超时，请检查日志: $COMPOSE logs backend --tail=30"
exit 1
