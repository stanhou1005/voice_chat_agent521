#!/usr/bin/env bash
# ============================================================
# reload-config.sh — 编辑 config/.env 后重新加载配置
# 用法: vim config/.env 后再运行 ./scripts/reload-config.sh
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

set -a; source config/.env; set +a

echo "正在重启 backend 以加载新配置..."
$COMPOSE up -d --force-recreate backend

echo "等待 backend 就绪..."
ATTEMPTS=0
while [ $ATTEMPTS -lt 20 ]; do
    if curl -sk https://localhost/health 2>/dev/null | grep -q ok; then
        echo "[OK] 配置已更新，服务就绪"
        echo ""
        echo "注意: 部分配置（LLM/SiliconFlow API key）"
        echo "      可从前端「设置」页面直接修改，无需重启。"
        exit 0
    fi
    ATTEMPTS=$((ATTEMPTS + 1))
    sleep 3
done

echo "⚠ 启动超时，请检查日志: $COMPOSE logs backend --tail=30"
exit 1
