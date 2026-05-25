# Voice Chat Agent — Docker 部署指南

## 目录

- [1. 环境要求](#1-环境要求)
- [2. 项目文件结构](#2-项目文件结构)
- [3. 首次部署](#3-首次部署)
- [4. 创建登录用户](#4-创建登录用户)
- [5. 更新配置](#5-更新配置)
- [6. 日常运维](#6-日常运维)
- [7. 故障排查](#7-故障排查)

---

## 1. 环境要求

- **操作系统**: Linux（Ubuntu 20.04+ / Debian 11+ / CentOS 8+）
- **Docker Engine**: 20.10+
- **Docker Compose**: v2（`docker compose`）或 v1（`docker-compose`）
- **最低配置**: 2 核 CPU, 4 GB RAM, 20 GB 磁盘

### 安装 Docker（如未安装）

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
# 重新登录使权限生效
```

---

## 2. 项目文件结构

```
voice_chat_agent/
├── config/                       ← 外挂配置目录（需手动创建 .env）
│   └── .env.example              ← 配置模板，可提交 git
│   └── .env                      ← 真实配置（需手动创建，不提交 git）
├── scripts/                      ← 运维脚本
│   ├── deploy.sh                 ← 一键部署
│   ├── reload-config.sh          ← 更新配置并重启
│   └── create-user.sh            ← 创建登录用户
├── docker-compose.yml            ← 服务编排
├── backend/                      ← FastAPI 后端
│   └── Dockerfile
├── frontend/                     ← React 前端 + nginx
│   ├── Dockerfile                ← 多阶段构建
│   └── nginx.conf                ← 反向代理配置
├── pgdata/                       ← PostgreSQL 数据（自动创建）
└── DEPLOY.md                     ← 本文档
```

---

## 3. 首次部署

### 3.1 获取代码

```bash
git clone <your-repo-url> voice_chat_agent
cd voice_chat_agent
```

### 3.2 创建配置文件

```bash
# 从模板复制
cp config/.env.example config/.env
```

### 3.3 编辑配置文件

```bash
vim config/.env
```

需要填写的关键配置（**必填项**）：

```ini
# ── DeepSeek API ──────────────────────────
LLM_API_KEY=sk-your-deepseek-api-key-here    # 必填

# ── 硅基流动 API（语音识别+合成）─────────
SILICONFLOW_API_KEY=sk-your-siliconflow-key  # 必填

# ── Tavily Search API ─────────────────────
TAVILY_API_KEY=tvly-your-tavily-key          # 必填

# ── JWT 密钥 ─────────────────────────────
JWT_SECRET_KEY=改成随机长字符串至少32字符      # 生产环境务必修改

# ── PostgreSQL（通常保持默认即可）─────────
PG_HOST=postgres
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=postgres
PG_DB=voice_chat
```

### 3.4 执行部署

```bash
./scripts/deploy.sh
```

该脚本会自动完成：
1. 检测 Docker 环境
2. 检测 `config/.env` 是否存在（首次运行会提示创建）
3. 构建 Docker 镜像
4. 启动所有服务（postgres → backend → nginx）
5. 等待健康检查通过
6. 提示后续操作

部署成功后访问 `http://<服务器IP>` 即可看到登录页面。

### 3.5 手动部署（可选）

如果不使用 `deploy.sh`，也可以手动执行：

```bash
cp config/.env.example config/.env
vim config/.env

docker compose build --parallel
docker compose up -d

# 等待服务就绪（约 30 秒）
curl http://localhost/health
# 返回 {"status":"ok"} 表示就绪
```

---

## 4. 创建登录用户

部署完成后需要创建一个管理员账号：

```bash
./scripts/create-user.sh
```

按提示输入用户名和密码。或者直接指定：

```bash
./scripts/create-user.sh --username admin --password your_password
```

### 修改密码

再次运行 `create-user.sh` 并指定已存在的用户名，会覆盖旧密码：

```bash
./scripts/create-user.sh --username admin --password new_password
```

---

## 5. 更新配置

### 5.1 修改 API Key 等环境变量

当需要更换 DeepSeek Key、SiliconFlow Key 等环境变量时：

```bash
# 1. 编辑配置文件
vim config/.env

# 2. 重新加载配置（重启 backend 容器）
./scripts/reload-config.sh
```

### 5.2 通过 Web 界面修改

部分配置（模型名、Tavily Key、代理地址）可以在前端"设置"页面直接修改，**即时生效无需重启**。

点击页面右上角齿轮图标 → 修改 → 保存。

---

## 6. 日常运维

### 查看服务状态

```bash
docker compose ps
```

### 查看日志

```bash
# 所有服务
docker compose logs -f

# 只看后端
docker compose logs -f backend

# 最近 100 行
docker compose logs --tail=100
```

### 重启服务

```bash
# 重启所有
docker compose restart

# 重启单个
docker compose restart backend
```

### 停止服务

```bash
docker compose down
```

### 停止并删除数据（危险操作）

```bash
docker compose down -v    # 会删除 PostgreSQL 数据和聊天记录
rm -rf pgdata/            # 清理数据目录
```

### 数据备份

PostgreSQL 数据存储在宿主机的 `./pgdata/` 目录下，直接备份该目录即可：

```bash
tar -czf backup-$(date +%Y%m%d).tar.gz pgdata/ config/.env
```

### 升级应用

```bash
git pull                  # 拉取最新代码
docker compose build --no-cache
docker compose up -d --force-recreate
```

---

## 7. 故障排查

### 服务启动失败

```bash
# 查看所有容器状态
docker compose ps -a

# 查看具体服务日志
docker compose logs backend --tail=50
docker compose logs postgres --tail=50
```

### 健康检查失败

```bash
# 手动测试健康检查
curl http://localhost/health

# backend 内部健康检查
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"
```

### PostgreSQL 连接失败

```bash
# 确认 PostgreSQL 是否运行
docker compose ps postgres

# 进入容器测试连接
docker compose exec postgres pg_isready -U postgres -d voice_chat
```

### 端口被占用

默认使用 80 端口。如果端口被占用，可以在 `.env` 中添加：

```ini
NGINX_PORT=8080
```

然后重启 `docker compose up -d`。

### 容器无法访问外网 API

确保服务器能访问以下地址：
- `https://api.deepseek.com`
- `https://api.siliconflow.cn`
- `https://api.tavily.com`

```bash
# 测试网络连通性
curl -I https://api.deepseek.com
```

### WebSocket 连接断开

WebSocket 通过 nginx 代理，超时时间已设为 1 小时。如果频繁断开，检查 nginx 日志：

```bash
docker compose logs nginx --tail=30
```

---

## 快速参考（TL;DR）

```bash
# 部署
cp config/.env.example config/.env
vim config/.env
./scripts/deploy.sh
./scripts/create-user.sh

# 改配置
vim config/.env && ./scripts/reload-config.sh

# 日常
docker compose logs -f          # 看日志
docker compose ps               # 看状态
docker compose restart backend  # 重启
```
