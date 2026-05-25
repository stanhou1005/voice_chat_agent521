#!/usr/bin/env bash
# ============================================================
# deploy.sh — 首次部署 Voice Chat Agent
# 用法: ./scripts/deploy.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "========================================"
echo "  Voice Chat Agent — Docker 部署"
echo "========================================"
echo ""

# ── 1. 检查依赖 ──
if ! command -v docker &>/dev/null; then
    echo "❌ 未找到 docker，请先安装 Docker Engine"
    exit 1
fi

if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    echo "❌ 未找到 docker compose，请先安装 Docker Compose"
    exit 1
fi

echo "[OK] Docker 环境检查通过"
echo ""

# ── 2. 检查配置文件 ──
if [ ! -f config/.env ]; then
    echo "⚠ 未找到 config/.env，正在从模板创建..."
    cp config/.env.example config/.env
    echo ""
    echo "============================================"
    echo "  请编辑 config/.env 填入真实 API key："
    echo "    vim config/.env"
    echo "============================================"
    echo ""
    echo "编辑完成后，重新运行: ./scripts/deploy.sh"
    exit 0
fi

echo "[OK] 配置文件 config/.env 已就绪"
echo ""

# Source config for docker-compose variable substitution
set -a; source config/.env; set +a

# ── 3. 生成自签名 SSL 证书（HTTPS 是浏览器麦克风的硬性要求）──
SSL_DIR="frontend/ssl"
if [ ! -f "$SSL_DIR/selfsigned.crt" ]; then
    echo "正在生成 HTTPS 证书..."
    mkdir -p "$SSL_DIR"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/selfsigned.key" \
        -out "$SSL_DIR/selfsigned.crt" \
        -subj "/CN=localhost" 2>/dev/null
    echo "[OK] HTTPS 自签名证书已生成 ($SSL_DIR/)"
else
    echo "[OK] HTTPS 证书已存在"
fi
echo ""

# ── 4. 创建 docker-compose 变量文件（让 compose 能读到 .env）──
if [ ! -f .env ]; then
    ln -sf config/.env .env
    echo "[OK] 已链接 config/.env -> .env (供 docker compose 变量替换)"
fi
echo ""

# ── 5. 构建镜像 ──
echo "正在构建 Docker 镜像..."
$COMPOSE build --no-cache
echo "[OK] 镜像构建完成"
echo ""

# ── 6. 启动服务 ──
echo "正在启动服务..."
$COMPOSE up -d
echo ""

# ── 7. 等待健康检查通过 ──
echo "等待服务就绪..."
ATTEMPTS=0
MAX_ATTEMPTS=30
while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    if curl -sk https://localhost/health 2>/dev/null | grep -q ok; then
        echo ""
        echo "[OK] 所有服务已就绪"
        break
    fi
    ATTEMPTS=$((ATTEMPTS + 1))
    printf "."
    sleep 3
done

if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
    echo ""
    echo "⚠ 服务启动超时，请检查日志:"
    echo "   $COMPOSE logs --tail=50"
    exit 1
fi

# ── 8. 完成 ──
echo ""
echo "========================================"
echo "  部署完成！"
echo ""
echo "  创建管理员账号:"
echo "    ./scripts/create-user.sh"
echo ""
echo "  访问地址: https://$(hostname -I 2>/dev/null | awk '{print $1}' || ip route get 1 2>/dev/null | awk '{print $7; exit}' || echo '服务器IP')"
echo ""
echo "  ⚠ 浏览器会报证书警告，点击「高级 → 继续访问」即可"
echo ""
echo "  查看日志:"
echo "    $COMPOSE logs -f"
echo "========================================"
