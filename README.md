# 🤖 Jarvis — Personal AI Agent

A fully autonomous AI agent built from scratch using **LangChain** and **LangGraph**. Jarvis can search the web, run code, manage files, remember you across conversations, and reason through multi-step tasks — all from your terminal.

> Built as a hands-on learning project to deeply understand agent architecture, tool design, memory systems, and LangGraph state machines.

---

## ✨ Features

### 🧠 Agent Architecture
- **LangGraph state machine** — explicit nodes, edges, and conditional routing
- **Parallel tool execution** — independent tools run simultaneously via Send API
- **ReAct loop** — LLM decides which tools to use, in what order, and when to stop

### 🛠️ Tools (9 total)
| Tool | Description |
|------|-------------|
| `web_search` | Real-time web search via Tavily |
| `calculator` | Safe sandboxed math evaluation |
| `get_current_time` | Current date and time |
| `read_file` | Read any text file |
| `write_file` | Write files with auto directory creation |
| `run_python_code` | Write and execute Python with security review |
| `update_notes` / `read_notes` | Persistent user profile memory |
| `update_project_notes` / `read_project_notes` | Project-specific memory |
| `add_chat_summary` | Log conversation summaries |

### 🔒 Safety & Loop Detection
- **Hard iteration limit** — stops after 10 LLM iterations
- **LLM soft check** — detects repetitive tool call patterns every 4 calls
- **Execution timeout** — kills agent if running over 60 seconds
- **Human in the loop** — when stuck, Jarvis explains the problem and asks for guidance
- **Code security review** — separate LLM reviews all code before execution

### 🧩 Memory System
- **Sliding window** — keeps last 20 messages per chat
- **Summarization** — compacts old messages when limit is reached
- **Multi-chat** — separate chat histories per session
- **Project memory** — project-specific context and notes
- **Persistent user profile** — remembers who you are across all conversations

---

## 📁 Project Structure

```
jarvis/
├── agent/
│   └── core.py          # LangGraph state machine (agent brain)
├── tools/
│   ├── web_search.py    # Tavily web search
│   ├── calculator.py    # Safe math evaluation
│   ├── time_tool.py     # Current time
│   ├── file_ops.py      # File read/write
│   ├── code_executor.py # Python execution with security review
│   └── notes.py         # Persistent memory tools
├── memory/
│   ├── memory.py        # Save/load/summarize chat history
│   ├── chats/           # Per-chat history files
│   ├── projects/        # Project-specific memory
│   └── user_notes.json  # Global user profile
├── config.py            # All settings and API keys
├── main.py              # CLI entry point
└── .env                 # API keys (never commit this)
```

---

## 🚀 Setup

### 1. Clone the repo
```bash
git clone https://github.com/SohamNehra/jarvis.git
cd jarvis
```

### 2. Install dependencies (using uv)
```bash
uv venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux
uv add langchain langchain-anthropic langchain-openai langgraph tavily-python python-dotenv
```

### 3. Set up API keys
Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

### 4. Run Jarvis
```bash
# default chat
uv run main.py

# named chat session
uv run main.py --chat crypto

# project-specific chat
uv run main.py --project jarvis --chat debugging
```

---

## 💬 Usage Examples

```
You: search for the current bitcoin price and calculate how much 0.75 BTC is worth

You: write a Python script to analyze my CSV file and save a report to reports/analysis.txt

You: my name is Soham and I'm building an AI agent
# Jarvis saves this to your profile automatically

You: what do you know about me?
# Jarvis reads from persistent notes and answers
```

---

## ⚙️ Configuration

All settings live in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL_NAME` | `claude-haiku-4-5-20251001` | Main agent LLM |
| `LOOP_CHECK_MODEL` | `gpt-5.4-nano` | Loop detection LLM (cheap) |
| `SECURITY_CHECK_MODEL` | `gpt-5.4-nano` | Code security reviewer |
| `TEMPERATURE` | `0` | LLM randomness (0 = deterministic) |
| `AGENT_TIMEOUT_SECONDS` | `60` | Max execution time |
| `DEBUG` | `True` | Show tool timing logs |

Set `DEBUG = False` for clean output without timing logs.

---

## 🗺️ Roadmap (v2)

- [ ] **Multi-agent architecture** — supervisor + specialist agents (researcher, coder, writer)
- [ ] **React web UI** — chat interface with project sidebar and streaming responses
- [ ] **Docker sandbox** — fully isolated code execution environment
- [ ] **RAG memory** — vector store for semantic memory retrieval
- [ ] **Self-improving agent** — writes and proposes its own tools for human review
- [ ] **Streaming responses** — real-time token streaming in UI

---

## 🧱 Built With

- [LangChain](https://langchain.com) — LLM application framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) — Agent state machine
- [Anthropic Claude](https://anthropic.com) — Main agent LLM
- [OpenAI](https://openai.com) — Loop detection and security review
- [Tavily](https://tavily.com) — Real-time web search API
- [uv](https://github.com/astral-sh/uv) — Fast Python package manager

---

## 📖 Learning Goals

This project was built to deeply understand:
- How LLM agents actually work under the hood
- LangChain core concepts (chains, tools, memory)
- LangGraph state machines (nodes, edges, Send API)
- Production agent patterns (safety, memory, human-in-loop)
- Tool design and modularity

Every component was built from scratch and evolved iteratively — starting simple, then upgrading to production patterns.