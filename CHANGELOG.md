# 已知问题和解决记录

## 2026-05-21 — 项目 v1 完成

- 语音聊天机器人 v1 版本提交（e7e204c），前后端核心功能就绪
- LangGraph Plan-Execute-Replan 工作流实现
- ASR/TTS 硅基流动接入完成
- Tavily Web 搜索工具集成

### v1 架构决策

| 决策 | 结论 |
|------|------|
| ASR | 火山引擎 → 后续改为硅基流动 SenseVoiceSmall（免费） |
| TTS | 火山引擎 → 后续改为硅基流动 CosyVoice2-0.5B |
| LLM | DeepSeek V4 Pro（model/base_url/API Key 可配置） |
| 搜索 | Tavily Search，无结果不降级到 LLM 直接回答 |
| 取消 | asyncio.Event + checkpoint 回滚 |
| TTL | APScheduler 每凌晨 3 点清 14 天前数据 |

## 2026-05-22 ~ 05-23 — 检查点 + Store + 登录系统

- AsyncPostgresSaver 单例管理 + LangGraph Store 长期记忆
- SessionMeta 模型用于历史会话列表
- Graph 编译缓存优化
- Tavily 切换到 langchain_tavily
- JWT + bcrypt 登录认证系统
- User 模型 + users 表
- REST/WS 端点全线加鉴权

## 2026-05-24 — 容器化部署

- 三服务 docker-compose（postgres + backend + nginx）
- 多阶段前端构建（Node build → nginx）
- 配置外挂目录 `config/.env`，启动时同步到 DB
- deploy.sh / reload-config.sh / create-user.sh 运维脚本

## 2026-05-25 ~ 05-26 — Docker 部署调试 + 多用户系统 + 稳定性修复

### 一、Docker 部署阶段

| # | 问题 | 根因 | 解决方案 | 涉及文件 |
|---|------|------|---------|---------|
| 1 | `docker compose build` 拉取 `python:3.12-slim` 失败 | `/etc/docker/daemon.json` 配了不可用的镜像源 `docker.xuanyuan.me` | 清理 `registry-mirrors`，或换用可用镜像源，重启 docker | 服务器配置 |
| 2 | backend 启动报 `libpq library not found` | `python:3.12-slim` 缺少 PostgreSQL 客户端库，psycopg 无法编译 | `backend/Dockerfile` 增加 `apt-get install gcc libpq-dev` | `backend/Dockerfile` |
| 3 | nginx 容器启动失败：端口 80 被占用 | 宿主机有旧容器或系统 nginx 残留 | 清理残留容器 `docker rm -f`；端口改为变量化配置 `${NGINX_HTTP_PORT:-80}` | `docker-compose.yml` |
| 4 | `NGINX_PORT` 配置不生效，nginx 仍抢占 80 | `docker compose` 的 `${VAR}` 只读项目根目录 `.env`，不读 `config/.env` | `deploy.sh` 中 `ln -sf config/.env .env` 创建软链接 | `scripts/deploy.sh` |
| 5 | 前端页面加载后正常，登录后一片深蓝白屏 | `crypto.randomUUID()` 在 HTTP 环境下浏览器不提供（需安全上下文） | 新增 `frontend/src/utils/uuid.js` polyfill，App.jsx / Sidebar.jsx 改用 `generateUUID()` | `frontend/src/utils/uuid.js`, `App.jsx`, `Sidebar.jsx` |
| 6 | 麦克风报错 `getUserMedia undefined` | 浏览器要求 HTTPS 才能使用麦克风 API | nginx 改为 HTTPS，`deploy.sh` 自动生成自签名证书 | `frontend/nginx.conf`, `frontend/Dockerfile`, `scripts/deploy.sh` |
| 7 | nginx 构建报 `COPY ssl: not found` | 证书生成在 `nginx/ssl/`，但 Dockerfile 上下文在 `frontend/` | 证书移到 `frontend/ssl/`，Dockerfile 从 `ssl/` 拷贝 | `frontend/Dockerfile` |
| 8 | 443 端口也被占用 | 宿主机有其他服务 | 默认 HTTPS 端口改为 8443，删掉 HTTP 80 端口映射，nginx 只监听 443（容器内） | `docker-compose.yml`, `frontend/nginx.conf` |
| 9 | nginx 健康检查失败 | `nginx:alpine` 镜像 `wget` 不可用或 HTTPS 未就绪 | 健康检查改为只走 HTTPS | `frontend/Dockerfile`, `docker-compose.yml` |
| 10 | `docker-compose.yml` 每次输出 `version is obsolete` 警告 | Compose v2 不需要 `version` 字段 | 删除 `version: '3.8'` 行 | `docker-compose.yml` |

### 二、Agent 对话逻辑

| # | 问题 | 根因 | 解决方案 | 涉及文件 |
|---|------|------|---------|---------|
| 11 | 两轮不同话题的对话，第二轮回答复读了第一轮的内容 | `past_steps` 用了 `operator.add` 累加器，跨轮不自动清空，导致新问题用旧结果 | `past_steps` 改为 plain list，每轮 `run_agent()` 入口清空；`execute_step` 手动累加 | `agent/tools.py`, `agent/nodes.py`, `agent/graph.py` |

### 三、多用户与权限

| # | 问题 | 根因 | 解决方案 | 涉及文件 |
|---|------|------|---------|---------|
| 12 | 无用户系统，所有人共享会话 | 无角色、无会话归属 | 加 User.role 字段、JWT 含 role、session 存 user_id、列表按 user 过滤 | 见下文需求对应 |
| 13 | 两个标签页分别登录不同用户，后登录的覆盖前者 | `localStorage` 同浏览器跨标签页共享 | 改为 `sessionStorage`，每标签页独立 | `frontend/src/services/auth.js` |

### 四、交互体验

| # | 问题 | 根因 | 解决方案 | 涉及文件 |
|---|------|------|---------|---------|
| 14 | 用户开始新提问时，上一轮 TTS 语音还在播放 | 没有在新提问开始时停止旧音频 | `useWebSocket.js` 加 `audioRef` + `window.__stopAudio()`；`ChatPanel._start()` 调用停止 | `hooks/useWebSocket.js`, `ChatPanel.jsx` |

---

## 已实现功能清单

### 认证系统
- JWT + bcrypt 登录
- `users` 表（PostgreSQL / Tortoise-ORM）
- CLI 脚本创建用户: `python -m scripts.create_user --username xxx --password xxx --role admin|user`
- 管理员 vs 普通用户角色

### 用户管理（admin）
- 创建 / 删除用户（前端弹窗）
- 修改自己密码（设置弹窗）
- 重置他人密码（用户管理弹窗）

### 会话隔离
- 每个用户只能看到自己的会话历史
- WebSocket 连接时绑定 user_id 到 session
- REST API 按 user_id 过滤 + 所有权校验

### 部署
- `./scripts/deploy.sh` 一键部署
- 自动生成自签名 SSL 证书
- 自动创建默认管理员 `admin / admin123`
- HTTPS 8443 端口，纯 SSL 无 HTTP
- `./scripts/reload-config.sh` 配置热更新
- `./scripts/create-user.sh` 手动创建用户

### Docker 架构
- postgres:16-alpine（数据持久化 `./pgdata`）
- backend（FastAPI + LangGraph + ASR/TTS）
- nginx（React 静态文件 + 反向代理 + WebSocket）
- 三服务健康检查 + 自动重启
