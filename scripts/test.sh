#!/usr/bin/env bash
# ============================================================
# test.sh — 全量回归测试
# 每次修改代码后运行，确保不改坏已有功能
# 用法: ./scripts/test.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
PASS=0
FAIL=0

green() { echo -e "\033[32m$1\033[0m"; }
red()   { echo -e "\033[31m$1\033[0m"; }

check() {
    if [ "$1" -eq 0 ]; then
        green "  PASS: $2"
        PASS=$((PASS + 1))
    else
        red "  FAIL: $2"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================="
echo " Voice Chat Agent — 回归测试"
echo "========================================="
echo ""

# ── 1. 后端 Python 语法 / 导入检查 ──
echo "[1/5] 后端模块导入检查"

cd backend

python -c "
from app.config import DATABASE_URL, JWT_SECRET_KEY, DEEPSEEK_API_KEY, SILICONFLOW_API_KEY
from app.models.user import User
from app.models.settings import Settings
from app.models.session import SessionMeta
from app.core.auth import hash_password, verify_password, create_access_token, verify_token, get_current_user, get_current_admin
from app.api.auth import router as auth_router
from app.api.rest import router as rest_router
from app.api.ws import router as ws_router
print('All imports OK')
" 2>&1
check $? "所有模块导入"

# ── 2. 认证逻辑单元测试 ──
echo "[2/5] 认证逻辑（hash / JWT / role）"

python -c "
from app.core.auth import hash_password, verify_password, create_access_token, verify_token
import jwt as j

# bcrypt
h = hash_password('test')
assert verify_password('test', h), 'verify failed'
assert not verify_password('wrong', h), 'wrong password accepted'
print('  bcrypt: OK')

# JWT with role
token = create_access_token(1, 'admin', 'admin')
payload = verify_token(token)
assert payload['role'] == 'admin'
assert payload['username'] == 'admin'
print('  JWT role: OK')

# Expired token
import time
expired = j.encode({'sub': '1', 'exp': 1}, 'change-me-in-production', algorithm='HS256')
try:
    verify_token(expired)
    assert False, 'should have raised'
except j.ExpiredSignatureError:
    print('  Expired rejection: OK')

# Bad signature
bad = j.encode({'sub': '1'}, 'wrong-key', algorithm='HS256')
try:
    verify_token(bad)
except j.InvalidSignatureError:
    print('  Bad signature rejection: OK')

print('Auth unit tests passed')
" 2>&1
check $? "认证逻辑单元测试"

# ── 3. 跨轮状态隔离测试 ──
echo "[3/5] Agent 跨轮 past_steps 隔离"

python verify_turn_isolation.py 2>&1
check $? "跨轮隔离（past_steps 不泄漏 + messages 保留）"

# ── 4. 前端构建 ──
echo "[4/5] 前端构建"

cd ../frontend
npm run build 2>&1 | tail -1
check ${PIPESTATUS[0]} "Vite 构建"
cd ..

# ── 5. 脚本语法检查 ──
echo "[5/5] Shell 脚本语法"

for f in scripts/*.sh; do
    bash -n "$f" 2>&1
done
check $? "Shell 脚本语法"

# ── 结果汇总 ──
echo ""
echo "========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
    red "  存在失败项，请检查并修复后再提交"
    exit 1
else
    green "  全部通过"
    exit 0
fi
