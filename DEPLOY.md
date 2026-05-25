# Voice Chat Agent — 部署指南

## 环境要求

- **Linux**（Ubuntu 20.04+ / Debian 11+ / CentOS 7+）
- **Docker Engine** 20.10+，**Docker Compose** v2
- **OpenSSL**（用于生成 HTTPS 证书）
- 最低 2 核 / 4 GB / 20 GB

> 浏览器麦克风 API 要求 HTTPS（localhost 除外），所以必须配置 SSL 证书才能使用语音功能。

## 快速部署（3 步）

```bash
# 1. 创建并编辑配置
cp config/.env.example config/.env
vim config/.env        # 填入 DeepSeek / SiliconFlow / Tavily API key

# 2. 一键部署（生成证书 + 构建镜像 + 启动服务）
./scripts/deploy.sh

# 3. 创建登录账号
./scripts/create-user.sh
```

然后访问 `https://<服务器IP>`，忽略证书警告点"继续访问"。

## 文件结构

```
voice_chat_agent/
├── config/
│   ├── .env.example       ← 配置模板（可提交 git）
│   └── .env               ← 真实配置（不入 git，挂载到容器 /config）
├── frontend/ssl/           ← 自签名证书（deploy.sh 自动生成）
├── scripts/
│   ├── deploy.sh           ← 一键部署
│   ├── reload-config.sh    ← 更新配置重启 backend
│   └── create-user.sh      ← 创建登录用户
├── docker-compose.yml
├── backend/Dockerfile
├── frontend/Dockerfile     ← 多阶段构建（Node build → nginx）
├── frontend/nginx.conf     ← HTTPS + 反向代理配置
├── pgdata/                 ← PostgreSQL 数据（自动创建）
└── DEPLOY.md
```

## 端口说明

| 端口 | 用途 | 说明 |
|------|------|------|
| 80 | HTTP → HTTPS 重定向 | 可选，如被占用可关 |
| 443 | HTTPS | 主入口，证书为自签名 |

如 80/443 被占用，在 `config/.env` 末尾加：

```ini
NGINX_HTTP_PORT=8080
NGINX_HTTPS_PORT=8443
```

## 创建用户

```bash
# 交互式
./scripts/create-user.sh

# 命令行指定
./scripts/create-user.sh admin mypassword
```

已存在的用户名再次执行会覆盖密码。

## 更新配置

| 改什么 | 需要重启？ | 方法 |
|--------|-----------|------|
| Tavily key / Model name | 否 | 前端"设置"页面直接改 |
| LLM_API_KEY / SILICONFLOW_API_KEY | 是 | `vim config/.env` → `./scripts/reload-config.sh` |
| 数据库密码 / JWT 密钥 | 是 | `vim config/.env` → `./scripts/reload-config.sh` |

## 常用运维命令

```bash
docker compose ps                    # 服务状态
docker compose logs -f               # 实时日志
docker compose logs backend --tail=50  # 只看后端
docker compose restart backend       # 重启单个服务
docker compose down                  # 停止所有服务
docker compose up -d                 # 启动
```

## 数据备份

```bash
tar -czf backup-$(date +%Y%m%d).tar.gz pgdata/ config/.env
```

## 故障排查

### 镜像拉取失败

检查 `/etc/docker/daemon.json` 里的 `registry-mirrors` 是否可用：

```bash
cat /etc/docker/daemon.json
# 清理不可用的 mirror 后重启 docker
sudo systemctl restart docker
```

### 端口被占用

```bash
ss -tlnp | grep -E ':80|:443'
# 停掉占用进程，或在 config/.env 配备用端口
```

### 登录后页面白屏

F12 → Console → 确认没有 JavaScript 报错。通常是缓存问题，Ctrl+Shift+R 强制刷新。

### 麦克风报错 getUserMedia undefined

说明当前不是 HTTPS。确认地址栏是 `https://` 开头，不是 `http://`。

### backend 启动报 libpq 缺失

确认 `backend/Dockerfile` 中有 `apt-get install -y gcc libpq-dev`。这是 psycopg 的底层依赖。
