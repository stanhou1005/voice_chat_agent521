# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start everything (PostgreSQL + backend + frontend)
docker-compose up -d postgres
cd backend && python manage.py start

# Status / stop
python manage.py status
python manage.py stop

# Backend dev (manual)
cd backend && uvicorn app.main:app --reload --port 8000
# Or on Windows: python run.py

# Frontend dev (manual)
cd frontend && npm run dev        # http://localhost:5173

# Run verification scripts (requires PostgreSQL running)
cd backend
python verify_checkpointer.py     # LangGraph checkpoint/store integration
python verify_speech.py           # ASR + TTS end-to-end
python verify_store.py            # Session history CRUD

# Frontend build
cd frontend && npm run build

# Tavily CLI search test
cd backend && python search.py "your query"
```

## Architecture

**Voice chat bot** — Chinese + English. Browser captures audio (VAD, push-to-talk), backend runs ASR → LangGraph agent → TTS, returns text + speech to frontend via WebSocket. DeepSeek for LLM, SiliconFlow for ASR/TTS, Tavily for web search.

### Data flow

```
Browser mic → useRecorder.js (16kHz mono WAV) → Base64
  → WebSocket {type:"audio", data:"<base64>"}
  → ws.py decodes → asr.py (SenseVoiceSmall via SiliconFlow)
  → agent/graph.py (Plan-Execute-Replan loop)
  → tts.py (CosyVoice2 via SiliconFlow) → Base64 MP3
  → WebSocket {type:"bot_audio", data:"<base64>"} → browser playback
```

### LangGraph agent (Plan-Execute-Replan)

```
START → planner (Pro) → agent/executor (Flash) → replan (Pro)
                                                    ├── response → END
                                                    └── next_steps → loop back to executor
```

- **Pro model** (`deepseek-v4-pro`): planner + replanner — needs strong reasoning, structured JSON output
- **Flash model** (`deepseek-v4-flash`): executor — ReAct agent with tool calling, 3-5x faster
- State: `messages` (add_messages reducer), `plan`, `past_steps` (operator.add), `response`
- Cancellation: `asyncio.Event` per session, checked at each node start, rolls back checkpoint on cancel
- Checkpointer: `AsyncPostgresSaver` singleton (`db/langgraph.py`), one per app lifecycle

### Database (PostgreSQL)

| Table | Manager | Purpose |
|-------|---------|---------|
| `settings` | Tortoise-ORM | Single-row model config (model_name, base_url, api_key, tavily_key, proxy_url) |
| `session_meta` | Tortoise-ORM | Session list metadata (thread_id, title, created_at, last_active_at, message_count) |
| `checkpoints` | AsyncPostgresSaver | LangGraph checkpoint snapshots |
| `checkpoint_writes` | AsyncPostgresSaver | Pending writes |
| `checkpoint_blobs` | AsyncPostgresSaver | Channel data blobs |

TTL cleanup: APScheduler daily at 3 AM deletes records older than 14 days. REST queries also filter by `created_at > NOW() - 14 days`.

### WebSocket protocol (`/ws/{session_id}`)

Client → Server: `audio`, `cancel`, `ping`
Server → Client: `asr_result`, `status` (phase + text), `thinking` (start/stop), `bot_text`, `bot_audio`, `cancelled`, `error`, `pong`

### Frontend state

React Context + useReducer, no Redux/Zustand. `sessionStates` isolated per session ID — switching tabs doesn't close other WebSocket connections (pool in `App.jsx`). Sidebar polls `GET /api/sessions` every 5s.

### Key backend files

| File | Role |
|------|------|
| `backend/app/main.py` | FastAPI entry, lifespan (Tortoise init + checkpointer + scheduler) |
| `backend/app/config.py` | `.env` loading, all config constants |
| `backend/app/api/ws.py` | WebSocket endpoint, message dispatch, cancel handling |
| `backend/app/api/rest.py` | REST CRUD for sessions + settings |
| `backend/app/agent/graph.py` | LangGraph graph construction, `run_agent()` entry point |
| `backend/app/agent/nodes.py` | `plan_step`, `execute_step`, `replan_step` |
| `backend/app/agent/tools.py` | `AgentState` TypedDict, `tavily_search_tool`, `get_current_datetime` |
| `backend/app/agent/prompts.py` | System prompts for planner/executor/replanner |
| `backend/app/services/asr.py` | SiliconFlow SenseVoiceSmall HTTP call |
| `backend/app/services/tts.py` | SiliconFlow CosyVoice2 HTTP call |
| `backend/app/db/langgraph.py` | Checkpointer + Store singleton management |
| `backend/app/db/cleanup.py` | APScheduler TTL cleanup job |
| `backend/app/utils/cancellation.py` | Per-session asyncio.Event cancel registry |

### Windows-specific notes

- `main.py` sets `WindowsSelectorEventLoopPolicy` — required for psycopg/asyncpg
- `manage.py` uses `taskkill` on Windows instead of `kill -9`
- `run.py` wraps uvicorn for Windows compatibility
- Use `npm.cmd` on Windows for frontend commands

---

## Rules

These rules apply to every task in this project unless explicitly overridden.
Bias: caution over speed on non-trivial work. Use judgment on trivial tasks.

### Rule 1 – Think Before Coding
State assumptions explicitly. If uncertain, ask rather than guess.
Present multiple interpretations when ambiguity exists.
Push back when a simpler approach exists.
Stop when confused. Name what's unclear.

### Rule 2 – Simplicity First
Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked. No abstractions for single-use code.
Test: would a senior engineer say this is overcomplicated? If yes, simplify.

### Rule 3 – Surgical Changes
Touch only what you must. Clean up only your own mess.
Don't "improve" adjacent code, comments, or formatting.
Don't refactor what isn't broken. Match existing style.

### Rule 4 – Goal-Driven Execution
Define success criteria. Loop until verified.
Don't follow steps. Define success and iterate.
Strong success criteria let you loop independently.

### Rule 5 – Use the model only for judgment calls
Use me for: classification, drafting, summarization, extraction.
Do NOT use me for: routing, retries, deterministic transforms.
If code can answer, code answers.

### Rule 6 – Token budgets are not advisory
Per-task: 4,000 tokens. Per-session: 30,000 tokens.
If approaching budget, summarize and start fresh.
Surface the breach. Do not silently overrun.

### Rule 7 – Surface conflicts, don't average them
If two patterns contradict, pick one (more recent / more tested).
Explain why. Flag the other for cleanup.
Don't blend conflicting patterns.

### Rule 8 – Read before you write
Before adding code, read exports, immediate callers, shared utilities.
"Looks orthogonal" is dangerous. If unsure why code is structured a way, ask.

### Rule 9 – Tests verify intent, not just behavior
Tests must encode WHY behavior matters, not just WHAT it does.
A test that can't fail when business logic changes is wrong.

### Rule 10 – Checkpoint after every significant step
Summarize what was done, what's verified, what's left.
Don't continue from a state you can't describe back.
If you lose track, stop and restate.

### Rule 11 – Match the codebase's conventions, even if you disagree
Conformance > taste inside the codebase.
If you genuinely think a convention is harmful, surface it. Don't fork silently.

### Rule 12 – Fail loud
"Completed" is wrong if anything was skipped silently.
"Tests pass" is wrong if any were skipped.
Default to surfacing uncertainty, not hiding it.
