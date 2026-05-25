#!/usr/bin/env bash
# ============================================================
# create-user.sh — 创建登录用户
# 用法: ./scripts/create-user.sh
#       或 ./scripts/create-user.sh --username myuser --password mypass
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

USERNAME="${1:---username}"
PASSWORD="${2:---password}"

if [ "$USERNAME" = "--username" ]; then
    read -rp "用户名: " USERNAME
    read -rsp "密码: " PASSWORD
    echo ""
fi

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    echo "用法: $0 <用户名> <密码>"
    echo "  或: $0 --username myuser --password mypass"
    exit 1
fi

echo "正在创建用户 '$USERNAME'..."
$COMPOSE exec -T backend python -m scripts.create_user --username "$USERNAME" --password "$PASSWORD"
echo "[OK] 完成"
