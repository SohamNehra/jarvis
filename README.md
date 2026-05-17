# 🤖 Jarvis — Personal AI Agent

A fully autonomous AI agent built from scratch using **LangChain**, **LangGraph**, **FastAPI**, and **Next.js**. Jarvis can search the web, execute code, manage files, remember you across conversations, orchestrate multiple specialist agents in parallel, and stream responses with live tool indicators — all from a clean web UI.

> Built as a hands-on learning project to deeply understand agent architecture, multi-agent orchestration, memory systems, and production streaming patterns. Every component built from scratch, every pattern understood.

---

## ✨ Features

### 🧠 Agent Architecture
- **LangGraph state machine** — explicit nodes, edges, and conditional routing
- **Parallel tool execution** — independent tools run simultaneously via Send API
- **Dynamic agent factory** — create any specialist agent in 3 lines
- **Multi-agent supervisor** — dynamically spawns specialist agents based on task
- **Streaming DAG execution** — dependent tasks start the moment their dependencies complete
- **Smart routing** — LLM decides single vs multi-agent based on task complexity
- **Loop detection** — LLM soft check every 4 tool calls detects repetitive patterns
- **Human in the loop** — when stuck, Jarvis explains the problem and asks for guidance
- **Execution timeout** — 300s hard limit with graceful escalation to supervisor

### 🛠️ Tools (11 total)
| Tool | Description |
|------|-------------|
| `web_search` | Real-time web search via Tavily |
| `calculator` | Safe sandboxed math evaluation |
| `get_current_time` | Current date and time |
| `read_file` | Read any text file |
| `write_file` | Write files with auto directory creation |
| `run_python_code` | Write and execute Python with LLM security review |
| `update_notes` / `read_notes` | Persistent user profile memory |
| `update_project_notes` / `read_project_notes` | Project-specific memory |
| `add_chat_summary` | Log conversation summaries |

### 🧩 Memory System
- **Sliding window** — keeps last 20 messages per chat with summarization
- **Multi-chat** — separate history per session, organized by project
- **Project memory** — each project has its own context and notes
- **User profile** — persistent facts about you across all conversations
- **Runtime config** — `.jarvis_config.json` for credential management

### 🔒 Safety & Guardrails
- **Code security review** — separate LLM reviews all code before execution
- **Loop detection** — LLM soft check every 4 tool calls
- **Execution timeout** — stops runaway tasks gracefully
- **Human in the loop** — LLM explains where it's stuck and asks for guidance
- **Rate limiting** — semaphore controls parallel API calls

### 🌐 Web UI
- **Streaming responses** — tokens render as they arrive
- **Tool indicators** — live display of which tools are running with timing
- **Project sidebar** — create, rename, move, delete chats and projects
- **Markdown rendering** — code blocks, bold, lists, all rendered correctly
- **Multi-agent toggle** — force multi-agent mode for complex tasks
- **Chat history** — persists across sessions, loads on refresh

---

## 📁 Project Structure

```
jarvis/                          # Python backend
├── agent/
│   ├── core.py                  # LangGraph state machine (single agent)
│   ├── supervisor.py            # Multi-agent supervisor with streaming DAG
│   ├── agent_factory.py         # Dynamic agent creation
│   └── specialists/             # Pre-built specialist agents
├── tools/
│   ├── web_search.py
│   ├── calculator.py
│   ├── time_tool.py
│   ├── file_ops.py
│   ├── code_executor.py         # Python execution with security review
│   └── notes.py
├── memory/
│   ├── memory.py                # Save/load/summarize chat history
│   ├── chats/                   # Per-chat history files
│   ├── projects/                # Project-specific memory
│   └── user_notes.json          # Global user profile
├── api/
│   ├── main.py                  # FastAPI app
│   ├── models.py                # Request/response schemas
│   └── routes/
│       ├── chat.py              # SSE streaming endpoints
│       ├── projects.py          # Project/chat management
│       └── memory.py            # Notes and settings endpoints
├── config.py                    # Settings and API keys
├── main.py                      # CLI entry point
├── run_api.py                   # API server entry point
└── .env                         # API keys (never commit)

jarvis-ui/                       # Next.js frontend
├── src/
│   ├── app/                     # Next.js App Router pages
│   ├── components/
│   │   ├── ChatPage.tsx         # Main chat with SSE streaming
│   │   ├── ChatArea.tsx         # Message rendering
│   │   ├── Sidebar.tsx          # Projects and chats
│   │   ├── ToolIndicator.tsx    # Live tool execution display
│   │   ├── ChatInput.tsx        # Input with multi-agent toggle
│   │   └── SettingsPage.tsx     # API key management
│   └── lib/
│       ├── api.ts               # API client
│       └── types.ts             # TypeScript interfaces
```

---

## 🚀 Setup

### Backend

**1. Clone the repo**
```bash
git clone https://github.com/sohamnehra/jarvis.git
cd jarvis
```

**2. Install dependencies**
```bash
uv venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux
uv add langchain langchain-anthropic langchain-openai langgraph tavily-python fastapi uvicorn python-multipart
```

**3. Set up API keys**

Create a `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

**4. Run the backend**
```bash
uv run run_api.py
```

Backend runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### Frontend

**1. Clone the frontend repo**
```bash
git clone https://github.com/sohamnehra/jarvis-ui.git
cd jarvis-ui
npm install
```

**2. Run the frontend**
```bash
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## 💬 Usage Examples

```
# Simple tool use
You: what time is it in Tokyo right now?

# Multi-step reasoning
You: search for bitcoin price, calculate how much 0.75 BTC is worth, and tell me the time

# File operations
You: search for the top 5 AI frameworks and write a comparison report to reports/ai_frameworks.txt

# Code execution
You: write python code to calculate fibonacci sequence up to 20 numbers

# Multi-agent (automatic or forced)
You: research the top 3 cryptocurrencies, analyze their 30-day trends, and write a formal investment report
You: use multi agent to research X and write a report
```

---

## ⚙️ Configuration

All settings in `config.py`, overridable via `.jarvis_config.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL_NAME` | `claude-haiku-4-5-20251001` | Main agent LLM |
| `LOOP_CHECK_MODEL` | `gpt-4.1-nano` | Loop detection LLM |
| `SECURITY_CHECK_MODEL` | `gpt-4.1-nano` | Code security reviewer |
| `TEMPERATURE` | `0` | LLM randomness |
| `AGENT_TIMEOUT_SECONDS` | `300` | Max execution time |
| `MAX_PARALLEL_AGENTS` | `3` | Rate limit for multi-agent |
| `DEBUG` | `False` | Show tool timing logs |

Set `DEBUG = True` to see tool timing and parallel execution logs.

---

## 🗺️ Roadmap (v3)

- [ ] **RAG memory** — Qdrant vector store for semantic retrieval across all history
- [ ] **Docker sandbox** — fully isolated code execution environment
- [ ] **Self-improving agent** — writes and proposes its own tools for human review
- [ ] **Shell execution** — run terminal commands with security guardrails
- [ ] **Browser automation** — Playwright-based web control
- [ ] **Always-on daemon** — Jarvis runs in background, message via WhatsApp/Telegram
- [ ] **Electron desktop app** — installable .exe/.dmg with settings UI

---

## 🧱 Built With

| Layer | Technology |
|-------|-----------|
| Agent framework | LangChain + LangGraph |
| Main LLM | Anthropic Claude Haiku |
| Routing + security | OpenAI GPT-4.1-nano |
| Web search | Tavily |
| Backend | FastAPI + Uvicorn |
| Frontend | Next.js 15 + TypeScript + Tailwind |
| Package manager | uv |

---

## 📖 What I Learned

Built to deeply understand:
- LangGraph state machines (nodes, edges, Send API, streaming updates)
- Multi-agent orchestration (supervisor pattern, streaming DAG, dependency resolution)
- Production streaming (SSE, token-by-token, tool events)
- Memory architecture (sliding window, summarization, multi-chat, project scoping)
- Tool design and security (sandboxed execution, LLM-based security review)
- FastAPI + Next.js full stack integration

Every concept introduced when a real limitation was felt — not from a tutorial.

---