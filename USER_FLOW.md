# Voice Chat Agent — 用户流程与系统调用说明

## 一、完整语音对话流程（7 阶段）

```
┌──────────────────────────────────────────────────────────────────────┐
│  阶段 1：麦克风采集（useRecorder.js）                                  │
│                                                                      │
│  用户点击 🎤 或按空格键 → MediaStream API 获取麦克风                  │
│  → AudioContext + ScriptProcessor 采集 16kHz 单声道 PCM               │
│  → RMS 能量检测（> -45 dBFS = 说话中）                                │
│  → 3 秒静音自动结束 / 用户点击 ⏹ 手动结束                             │
│  → 封装 WAV → Base64 编码                                            │
│  → 开始录音时自动停止上一轮还在播放的 TTS 语音（不串音）               │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  阶段 2：WebSocket 传输                                               │
│                                                                      │
│  客户端 → 后端: {"type":"audio", "data":"<base64_wav>"}               │
│  后端 ws.py 接收 → Base64 解码 → audio_bytes                          │
│  前端显示状态: "正在识别语音…"                                         │
└──────────────────────────────────────​────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  阶段 3：语音识别 ASR（services/asr.py）                               │
│                                                                      │
│  POST https://api.siliconflow.cn/v1/audio/transcriptions              │
│  模型: FunAudioLLM/SenseVoiceSmall                                    │
│  输入: WAV bytes → 输出: 文本字符串                                    │
│                                                                      │
│  发给前端: {"type":"asr_result", "text":"今天天气怎么样"}               │
│  空结果 → {"type":"error", "message":"未检测到语音内容"}               │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  阶段 4：LangGraph 智能体（agent/graph.py）                            │
│                                                                      │
│  Plan-Execute-Replan 循环架构：                                       │
│                                                                      │
│  plan_step (Pro)  → 拆解用户问题为有序步骤                             │
│       │                                                               │
│       ▼                                                               │
│  execute_step (Flash) → ReAct Agent 执行第 1 步                        │
│       │          ┌─ get_current_datetime() 获取日期                    │
│       │          └─ tavily_search_tool() Web 搜索                      │
│       ▼                                                               │
│  replan_step (Pro) → 评估结果，决定继续或完成                           │
│       │                                                               │
│       ├── 继续 → 返回剩余步骤，循环到 execute_step                      │
│       └── 完成 → 生成口语化最终答案                                    │
│                                                                      │
│  实时推送状态: "正在分析问题" → "正在执行: 搜索xxx" → "正在评估结果"     │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  阶段 5：文本回复                                                     │
│                                                                      │
│  发给前端:                                                            │
│  {"type":"bot_text", "text":"今天北京的天气晴朗，气温25°C..."}          │
│  {"type":"thinking", "status":"stop"}                                │
│  前端 ChatPanel 追加机器人文字气泡                                     │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  阶段 6：语音合成 TTS（services/tts.py）                               │
│                                                                      │
│  POST https://api.siliconflow.cn/v1/audio/speech                      │
│  模型: FunAudioLLM/CosyVoice2-0.5B                                    │
│  输入: 机器人回复文本 → 输出: MP3 bytes                                │
│  Base64 编码 → {"type":"bot_audio", "data":"<base64_mp3>"}           │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  阶段 7：语音播放（useWebSocket.js）                                   │
│                                                                      │
│  Base64 解码 → Blob → Audio.play()                                    │
│  播放完成后状态恢复为 idle，用户可进行下一轮对话                         │
│  用户开始新提问 → __stopAudio() 立即掐断当前播放                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 对话持久化

每次对话后：
1. **Checkpointer** 自动保存完整 state（messages + plan + past_steps）到 PostgreSQL
2. **Store** 更新 session 元数据（message_count + last_active_at）
3. 下次打开同一会话 → 从 checkpointer 恢复全部上下文

## 二、状态机

```
IDLE → RECORDING → PROCESSING → IDLE
                     ↓
                  CANCELLED → IDLE
```

| 状态 | 说明 |
|------|------|
| IDLE | 就绪，等待用户开始说话 |
| RECORDING | 正在录音，显示静音倒计时 |
| PROCESSING | 音频已发送，等待 ASR+LLM+TTS 全链路完成 |

## 三、LangGraph Agent 架构

### 图结构

```
START → planner (Pro) → agent/executor (Flash) → replan (Pro)
                                                    ├── response → END
                                                    └── next_steps → 循环 agent
```

### State 定义

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # 对话历史
    input: str                                # 当前用户问题
    plan: list[str]                           # 执行步骤
    past_steps: list[tuple]                   # (步骤, 结果) — 每轮重置
    response: str                             # 最终答案
```

### 两层模型策略

| 模型 | 节点 | 原因 |
|------|------|------|
| deepseek-v4-pro | planner, replanner | 复杂推理、结构化输出 |
| deepseek-v4-flash | executor (ReAct) | 工具调用只需快模型，3-5x 提速 |

### 取消机制

```
用户点击"终止" → {"type":"cancel"} → ws.py 设置 asyncio.Event
→ 每个节点开头 _check_cancelled() 检查
→ 抛出 CancelledError → 通知前端 → 重置标志
```

## 四、WebSocket 协议

端点: `wss://host/ws/{session_id}?token=<jwt>`

### 客户端 → 服务端

| type | 格式 |
|------|------|
| `audio` | `{"type":"audio", "data":"<base64_wav>", "timestamp":...}` |
| `cancel` | `{"type":"cancel"}` |
| `ping` | `{"type":"ping"}` |

### 服务端 → 客户端

| type | 格式 |
|------|------|
| `asr_result` | `{"type":"asr_result", "text":"...", "is_final":true}` |
| `status` | `{"type":"status", "phase":"asr\|plan\|search\|replan\|tts", "text":"..."}` |
| `thinking` | `{"type":"thinking", "status":"start\|stop"}` |
| `bot_text` | `{"type":"bot_text", "text":"..."}` |
| `bot_audio` | `{"type":"bot_audio", "data":"<base64_mp3>"}` |
| `cancelled` | `{"type":"cancelled"}` |
| `error` | `{"type":"error", "message":"..."}` |
| `pong` | `{"type":"pong"}` |

## 五、REST API

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | `/api/auth/login` | 无 | 登录 |
| GET | `/api/auth/users` | admin | 用户列表 |
| POST | `/api/auth/users` | admin | 创建用户 |
| DELETE | `/api/auth/users/{id}` | admin | 删除用户 |
| PUT | `/api/auth/users/{id}/password` | admin | 重置他人密码 |
| PUT | `/api/auth/password` | login | 修改自己密码 |
| GET | `/api/sessions` | login | 会话列表（仅自己） |
| GET | `/api/sessions/{id}/messages` | login | 消息历史 |
| DELETE | `/api/sessions/{id}` | login | 删除会话 |
| GET | `/api/settings` | login | 获取模型配置 |
| PUT | `/api/settings` | login | 更新模型配置 |
| GET | `/health` | 无 | 健康检查 |

## 六、前端状态管理

```javascript
state = {
  isAuthenticated: false,
  username: null,
  role: null,
  currentSessionId: "uuid",
  sessions: [...],           // 历史会话列表
  sessionStates: {           // 每会话独立
    "uuid": { messages: [...], status: "idle", statusText: "" }
  },
  settingsModalOpen: false,
  userManagementOpen: false,
  error: null,
};
```

- `sessionStates` 按 sessionId 隔离，切换标签页不影响其他连接
- WebSocket 连接池复用，不随会话切换而断开
- 登录态用 `sessionStorage`（同浏览器标签页间隔离，支持多用户同时使用）

## 七、音频规格

| 参数 | 值 |
|------|-----|
| 采样率 | 16000 Hz |
| 位深度 | 16-bit PCM |
| 声道 | Mono |
| 格式 | WAV → Base64 → JSON |
| VAD 阈值 | > -45 dBFS = 说话中 |
| 静音判定 | 连续 3 秒低于阈值 |
| 最短语音 | 1 秒 |
| 最长语音 | 30 秒 |
