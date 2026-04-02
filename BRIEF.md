# AI Project Assistant — Project Brief

## What is this?

An AI-powered project management assistant where users can:

- **Chat** with Claude about their projects (with full tool-calling support)
- **Generate images** via chat using OpenAI's gpt-image-1
- **Analyze images** using Google Gemini Vision
- **Persist project knowledge** across conversations via memory
- **Run a background agent** that auto-organizes all project data into structured notes

Built with **FastAPI** (Python), **Supabase** (PostgreSQL), and three AI models working together.

---

## How It Works (In Short)

```
User creates a project with a brief
        │
        ▼
User chats with Claude ──► Claude decides which tools to use:
        │                    ├── generate_image  → OpenAI
        │                    ├── analyze_image   → Gemini Vision
        │                    ├── save_memory     → Supabase
        │                    ├── get_memory      → Supabase
        │                    └── get_brief       → Supabase
        │
        ▼
All conversations, images, and memory are stored in Supabase
        │
        ▼
Background agent can be triggered to organize everything
into structured memory categories
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python) |
| Chat AI | Anthropic Claude |
| Image Generation | OpenAI gpt-image-1 |
| Image Analysis | Google Gemini Vision |
| Database | Supabase (PostgreSQL) |
| Frontend | Vanilla HTML/CSS/JS |

---

## Database Schema (6 Tables)

| Table | What it stores |
|-------|---------------|
| `projects` | Project name and ID |
| `project_briefs` | Title, description, goals, tech stack, audience (1:1 with project) |
| `conversations` | Chat messages (user + assistant) with tool call logs |
| `images` | Generated images linked to project, with cached analysis |
| `project_memory` | Key-value knowledge entries scoped per project |
| `agent_executions` | Background agent job status (pending/running/completed/failed) |

---

## Key Features

### 1. Tool Loop
When a user sends a chat message, Claude can invoke tools (generate image, save memory, etc.), receive results, and keep reasoning — looping until it has a final answer. Up to 10 iterations per message.

### 2. Multi-Model Orchestration
Three AI models collaborate:
- **Claude** orchestrates and reasons
- **OpenAI** generates images when Claude decides to
- **Gemini** analyzes images when Claude needs visual understanding

### 3. Sub-Agent Pattern
The background agent runs **asynchronously** (non-blocking). It collects all project data, sends it to Claude with a specialized prompt, and saves organized memory entries. Its status can be polled via API.

### 4. Persistent Memory
Claude checks project memory at the start of every conversation and saves important facts as it learns them. Memory is scoped per project and persists across sessions.

---

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env   # Fill in API keys

# 3. Run schema in Supabase SQL Editor
# (copy sql/schema.sql)

# 4. Start
uvicorn app.main:app --reload --port 8000

# 5. Open
# http://localhost:8000
```

---

## API Endpoints (Summary)

| Endpoint | What it does |
|----------|-------------|
| `POST /projects/` | Create project with brief |
| `POST /projects/{id}/chat/` | Chat with Claude (full tool loop) |
| `GET /projects/{id}/images/` | List generated images |
| `GET /projects/{id}/memory` | View project memory |
| `POST /projects/{id}/agent/trigger` | Run background agent |
| `GET /agent/status/{id}` | Poll agent status |
| `GET /health` | Check service connectivity |

For full details, see the main [README.md](README.md).
