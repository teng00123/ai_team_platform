# 🤖 AI Team Platform

> A multi-agent collaboration platform powered by OpenClaw — assemble your AI team and orchestrate complex tasks end-to-end.

[![CI](https://github.com/teng00123/ai_team_platform/actions/workflows/ci.yml/badge.svg)](https://github.com/teng00123/ai_team_platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey)](./LICENSE)

English | [中文](./README.zh.md)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧑‍💼 **Multi-Role Management** | Define any number of roles (PM, Architect, Engineer, QA…), each with its own system prompt and expertise |
| ⚡ **Persistent Sessions** | Every role holds an independent long-lived session — context and memory are preserved across tasks |
| 🎯 **Controller Orchestration** | A controller agent auto-decomposes tasks, dispatches sub-tasks to each role, and consolidates results |
| 📋 **Live Execution Logs** | Click any role card during a run to see real-time status and the full output in a side drawer |
| 📊 **Task History** | Browse all past orchestrations and drill into per-role results at any time |
| 🔌 **SSE Streaming** | Orchestration progress is pushed to the UI in real-time via Server-Sent Events |
| 🌐 **3D Command Center** | A Three.js visualization showing all agents, their states, and communication links |

---

## 🖥️ Preview

![AI Team Platform UI](docs/preview.png)

> Multi-role team panel · Controller orchestration · Real-time task history

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [OpenClaw](https://openclaw.ai) running locally (internal edition)
- OpenClaw Gateway Token (required for `sessions_spawn` / `sessions_send`)

### Install

```bash
git clone https://github.com/teng00123/ai_team_platform.git
cd ai_team_platform
pip install -r requirements.txt
```

### Initialize data directory

```bash
mkdir -p data
echo "{}" > data/roles.json
echo "{}" > data/tasks.json
```

### Run

```bash
python main.py
```

Open **http://localhost:8765** in your browser.

> 📝 Logs are written to `/tmp/ai_team.log`
> 📖 API docs available at **http://localhost:8765/docs**

---

### Run with Docker

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

Set environment variables in a `.env` file alongside `docker-compose.yml`:

```env
OPENCLAW_GATEWAY_PORT=23001
OPENCLAW_GATEWAY_TOKEN=your_token_here
```

---

## 📁 Project Structure

```
ai_team_platform/
├── main.py              # FastAPI entry point & REST routes
├── team_manager.py      # Core: orchestration engine & session pool
├── models.py            # Pydantic models (AgentRole / TeamTask / SubTaskResult)
├── cli.py               # CLI helper
├── static/
│   ├── index.html       # Single-page frontend (no build step)
│   ├── scene.html       # 3D Command Center (Three.js)
│   └── vendor/          # Third-party libs (read-only)
├── data/                # Runtime data — gitignored
│   ├── roles.example.json
│   └── tasks.example.json
├── docs/                # Documentation assets
├── .github/workflows/   # CI / Release / Dependency Review
├── requirements.txt
├── CONTRIBUTING.md
└── LICENSE
```

---

## 🔌 API Reference

### Role Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/roles` | List all roles |
| `POST` | `/api/roles` | Create a role (auto-spawns a persistent session) |
| `DELETE` | `/api/roles/:id` | Delete a role |
| `POST` | `/api/roles/:id/init-session` | Manually reset a role's session |

### Task Orchestration

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/tasks` | List all tasks |
| `POST` | `/api/orchestrate` | Start a multi-role orchestration (returns `task_id` immediately) |
| `GET` | `/api/tasks/:id` | Get task detail including all sub-task results |
| `GET` | `/api/tasks/:id/sub/:role_id` | Get a specific role's sub-task result |

### Real-time Events

| Path | Description |
|------|-------------|
| `GET /events` | SSE stream — orchestration progress pushed in real time |

---

## 🧩 Session Lifecycle

```
Role created
     │
     ▼
Auto-spawn persistent session (OpenClaw subagent)
     │
     ▼
session_key stored in role config
     │
     ├── Task arrives → sessions_send  (context preserved)
     │
     └── Session invalid → auto-respawn new subagent (graceful fallback)
```

Each role's persistent session remembers its identity and prior interactions — true role continuity across tasks.

---

## ⚙️ Configuration

### Gateway Tool Permissions

Add the following to your `openclaw.json`:

```json
{
  "gateway": {
    "tools": {
      "allow": [
        "sessions_spawn",
        "sessions_send",
        "sessions_history",
        "sessions_list"
      ]
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCLAW_GATEWAY_PORT` | `23001` | OpenClaw Gateway port |
| `OPENCLAW_GATEWAY_TOKEN` | _(auto-detected)_ | Gateway auth token (read from config if unset) |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | Local LLM endpoint (fallback) |
| `LLM_API_KEY` | `ollama` | API key for local LLM |

---

## 🏗️ Architecture

```
Frontend (SPA)
  │  Vanilla JS · Fetch API · SSE · Three.js
  │
  ▼
FastAPI Server  (main.py)
  │  REST API + SSE event stream
  │
  ▼
TeamManager  (team_manager.py)
  │  Orchestration engine · Role registry · Session pool
  │
  ├──→ OpenClaw Gateway  (sessions_spawn / sessions_send)
  │         └──→ Subagent  (one independent session per role)
  │
  └──→ Local LLM  (ollama — fallback when Gateway unavailable)
```

**Agent call priority:**

| Priority | Method | When |
|----------|--------|------|
| 1 | `sessions_send` | Persistent session alive — context preserved |
| 2 | `sessions_spawn` | Session expired or not yet created |
| 3 | Local LLM (ollama) | Gateway unavailable |
| 4 | Rule-based fallback | Last resort |

---

## 🗺️ Roadmap

- [x] Multi-role management
- [x] Controller-driven orchestration
- [x] Real-time execution drawer
- [x] Persistent role sessions with auto-recovery
- [x] Per-role sub-task result viewer
- [x] 3D Command Center visualization
- [ ] Peer-to-peer role messaging (no controller)
- [ ] Task template library
- [ ] Multi-team workspace support

---

## 🤝 Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for branch strategy, commit conventions, code style, and release workflow.

---

## 📄 License

[MIT](./LICENSE) © 2026 teng00123
