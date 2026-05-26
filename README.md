# Voice Chat Agent — 语音聊天机器人

纯语音交互的 AI 聊天机器人，支持中英文。浏览器采集语音 → ASR 识别 → LangGraph 智能体（Plan-Execute-Replan）→ TTS 合成 → 语音播放。

---

## 一、技术栈

| 层次 | 选型 | 用途 |
|------|------|------|
| 前端 | React 18 + Vite | SPA，深色主题，无 UI 框架 |
| 后端 | FastAPI + Uvicorn | WebSocket + REST API |
| ORM | Tortoise-ORM | `settings` 表 + `session_meta` 表 + `users` 表 |
| 智能体 | LangGraph 1.2 | Plan-Execute-Replan 循环 |
| LLM（规划/评估）| DeepSeek V4 Pro | Planner / Replanner 节点 |
| LLM（工具执行）| DeepSeek V4 Flash | Executor 节点（ReAct Agent） |
| ASR | 硅基流动 SenseVoiceSmall | 语音识别 |
| TTS | 硅基流动 CosyVoice2-0.5B | 语音合成 |
| 搜索 | Tavily Search | Web 搜索，advanced 深度 |
| 数据库 | PostgreSQL 16 | 所有持久化存储 |
| 部署 | Docker Compose | nginx + backend + postgres |

## 二、系统架构

```
浏览器 (HTTPS)
    │
    ▼
┌──────────┐     ┌──────────────┐     ┌──────────┐
│  nginx   │────▶│   backend    │────▶│ postgres  │
│  :8443   │     │   :8000      │     │ :5432     │
│  静态文件  │     └──────┬───────┘     └──────────┘
└──────────┘            │
                   ┌────┼────┐
                   │    │    │
              DeepSeek SiliconFlow Tavily
```

- **nginx**: HTTPS 终端（自签名证书），前端静态文件，`/api` + `/ws` 反向代理
- **backend**: FastAPI，JWT 认证，LangGraph Agent，ASR/TTS
- **postgres**: 用户表、会话元数据、LangGraph checkpoint + Store

## 三、项目目录

```
chat_agent521/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口 + lifespan
│   │   ├── config.py                # 环境变量配置
│   │   ├── api/
│   │   │   ├── ws.py                # WebSocket /ws/{session_id}
│   │   │   ├── rest.py              # REST /api/*
│   │   │   └── auth.py              # 登录 + 用户管理
│   │   ├── agent/
│   │   │   ├── graph.py             # LangGraph 图 + run_agent()
│   │   │   ├── nodes.py             # plan_step / execute_step / replan_step
│   │   │   ├── tools.py             # AgentState + Tavily + get_current_datetime
│   │   │   ├── prompts.py           # Planner / Executor / Replanner 提示词
│   │   │   └── status.py            # 状态回调
│   │   ├── services/
│   │   │   ├── asr.py               # SiliconFlow SenseVoiceSmall
│   │   │   ├── tts.py               # SiliconFlow CosyVoice2-0.5B
│   │   │   └── tavily.py            # Tavily 搜索封装
│   │   ├── models/
│   │   │   ├── settings.py          # 模型配置（单行）
│   │   │   ├── session.py           # 会话元数据
│   │   │   └── user.py              # 用户（含 role）
│   │   ├── core/
│   │   │   └── auth.py              # JWT + bcrypt + 鉴权依赖
│   │   ├── db/
│   │   │   ├── langgraph.py         # Checkpointer + Store 单例
│   │   │   └── cleanup.py           # TTL 定时清理
│   │   └── utils/
│   │       └── cancellation.py      # asyncio.Event 取消管理器
│   ├── scripts/
│   │   └── create_user.py           # CLI 创建用户
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # 根组件 + WebSocket Pool
│   │   ├── App.css                  # 全局样式
│   │   ├── context/AppContext.jsx   # 全局状态 Reducer
│   │   ├── components/
│   │   │   ├── Sidebar.jsx          # 左侧会话列表
│   │   │   ├── ChatPanel.jsx        # 右侧聊天面板
│   │   │   ├── LoginPage.jsx        # 登录页
│   │   │   ├── Message.jsx          # 消息气泡
│   │   │   ├── Thinking.jsx         # 状态提示 + 终止按钮
│   │   │   ├── SettingsModal.jsx    # 设置 + 修改密码
│   │   │   └── UserManagement.jsx   # 用户管理（admin）
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js      # WS 连接 + 消息分发 + 音频播放
│   │   │   └── useRecorder.js       # 按键说话录音器
│   │   ├── services/
│   │   │   ├── api.js               # REST API 封装
│   │   │   └── auth.js              # 登录态管理
│   │   └── utils/
│   │       └── uuid.js              # HTTP 兼容 UUID
│   ├── nginx.conf                   # 生产 nginx 配置
│   └── Dockerfile                   # 多阶段构建
├── config/
│   ├── .env.example                 # 配置模板
│   └── .env                         # 真实配置（不入 git）
├── scripts/
│   ├── deploy.sh                    # 一键部署
│   ├── reload-config.sh             # 配置热更新
│   ├── create-user.sh               # 创建用户
│   └── test.sh                      # 回归测试
├── docker-compose.yml
├── DEPLOY.md                        # 部署指南
├── CHANGELOG.md                     # 问题跟踪
└── README.md                        # 本文件
```

## 四、数据库

| 表 | 管理方 | 用途 |
|----|--------|------|
| `users` | Tortoise-ORM | 用户认证（id, username, password_hash, role） |
| `settings` | Tortoise-ORM | 模型配置单行（model_name, base_url, api_key, tavily_key, proxy_url） |
| `session_meta` | Tortoise-ORM | 会话元数据（thread_id PK, title, created_at, last_active_at, message_count） |
| `checkpoints` | AsyncPostgresSaver | LangGraph checkpoint 快照 |
| `checkpoint_writes` | AsyncPostgresSaver | Pending writes |
| `checkpoint_blobs` | AsyncPostgresSaver | Channel data blobs |
| Store 表 | AsyncPostgresStore | 长期记忆，Namespace `("sessions",)` |

TTL 清理：APScheduler 每天凌晨 3:00 删除 14 天前的记录。

## 五、认证体系

- JWT + bcrypt，登录接口 `POST /api/auth/login`
- 角色：admin / user
- admin 可创建/删除用户、重置密码
- 所有用户可在设置中修改自己密码
- 每用户会话隔离（session 绑定 user_id）

## 六、部署

详见 [DEPLOY.md](DEPLOY.md)。快速启动：

```bash
cp config/.env.example config/.env && vim config/.env
./scripts/deploy.sh
# 访问 https://服务器IP:8443，默认管理员 admin / admin123
```
