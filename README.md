# AI Project Assistant

An AI-powered project assistant built with **FastAPI**, **Claude (Anthropic)**, **Gemini (Google)**, **DALL-E (OpenAI)**, and **Supabase**. Users can create projects, chat with an AI assistant that has access to tools, generate and analyze images, persist project knowledge via memory, and trigger a background agent that organizes all project data into structured memory files.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Schema Design Decisions](#schema-design-decisions)
- [API Endpoints](#api-endpoints)
- [Tool Loop (Chat → Tools → Response)](#tool-loop)
- [Agent System](#agent-system)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Usage Examples](#usage-examples)

---

## Architecture Overview

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│   Client     │────▶│            FastAPI Backend               │
│  (API calls) │◀────│                                          │
└─────────────┘     │  ┌─────────┐  ┌────────┐  ┌──────────┐  │
                    │  │ Routers │──│Services│──│  Tools   │  │
                    │  └─────────┘  └────────┘  └──────────┘  │
                    │       │            │            │         │
                    │       ▼            ▼            ▼         │
                    │  ┌─────────┐  ┌────────┐  ┌──────────┐  │
                    │  │Supabase │  │ Claude │  │  DALL-E  │  │
                    │  │   (DB)  │  │  API   │  │   API    │  │
                    │  └─────────┘  └────────┘  └──────────┘  │
                    │                    │                      │
                    │               ┌────────┐                 │
                    │               │ Gemini │                 │
                    │               │ Vision │                 │
                    │               └────────┘                 │
                    └──────────────────────────────────────────┘
```

### Tech Stack
- **Python 3.11+** — Runtime
- **FastAPI** — Web framework with async support
- **Anthropic Claude** — Primary AI (chat, tool use, reasoning)
- **Google Gemini** — Image analysis (Vision model)
- **OpenAI DALL-E 3** — Image generation
- **Supabase (PostgreSQL)** — Database and storage

---

## Schema Design Decisions

### Tables

| Table | Purpose | Key Design Choice |
|-------|---------|-------------------|
| `projects` | Top-level entity | Minimal — just `id` and `name`. Everything else links here. |
| `project_briefs` | Project definition | Separated from `projects` (1:1, unique FK) for independent updates and future versioning support. Uses JSONB for `goals` and `reference_links` to avoid join tables. |
| `conversations` | Chat message history | Stores both `user` and `assistant` messages. `tool_calls` column (JSONB) preserves the full tool invocation chain for debugging and audit. |
| `images` | Generated images | Links to project. `analysis` column caches Gemini's vision output to avoid redundant API calls. |
| `project_memory` | Persistent knowledge | Key-value design (not free-text) enables targeted retrieval. `source` field tracks origin (`user`, `assistant`, or `agent`). Composite unique index on `(project_id, memory_key)` ensures no duplicate keys per project. |
| `agent_executions` | Background job tracking | Independent of the triggering mechanism. `task_type` field future-proofs for multiple agent types. `result` JSONB stores structured outcomes. |

### Why JSONB for goals/links?
PostgreSQL's JSONB allows flexible array storage without needing separate tables and many-to-many relationships. It's queryable, indexable, and perfect for lists of strings that don't need relational integrity.

### Why separate project_briefs from projects?
Decoupling allows brief updates without touching the project entity. It also supports future features like brief versioning, approval workflows, or multiple brief drafts.

### Why key-value memory instead of free-text?
Key-value memory (`memory_key` → `memory_value`) allows Claude to:
1. Retrieve specific facts quickly (e.g., "What was the preferred color scheme?")
2. Update individual pieces of knowledge without rewriting everything
3. Categorize information naturally (the key serves as the category)

---

## API Endpoints

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/` | Create a new project with a brief |
| `GET` | `/projects/` | List all projects |
| `GET` | `/projects/{id}` | Get a project with its brief |
| `PUT` | `/projects/{id}/brief` | Update a project's brief |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{id}/chat` | Send a message → Claude processes with tools → response |
| `GET` | `/projects/{id}/chat` | Get conversation history |

### Images
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects/{id}/images` | List all images for a project |
| `GET` | `/projects/{id}/images/{image_id}` | Get a specific image |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{id}/agent/trigger` | Trigger background agent |
| `GET` | `/agent/status/{execution_id}` | Poll agent execution status |

### Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects/{id}/memory` | View all stored memory entries |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Basic health check |
| `GET` | `/health` | Detailed health check with service status |

---

## Tool Loop

When a user sends a chat message, the following sequence occurs:

```
User Message
    │
    ▼
Load conversation history from DB
    │
    ▼
Send to Claude with tools defined
    │
    ▼
┌───────────────────────────────┐
│  Claude processes the message │
│                               │
│  stop_reason == "tool_use"?   │──── Yes ──▶ Execute tool
│         │                     │              │
│         No                    │              ▼
│         │                     │         Save result
│         ▼                     │              │
│  Return final text response   │◀─────────────┘
└───────────────────────────────┘    (loop back to Claude)
```

### Available Tools

1. **`generate_image`** — Calls DALL-E 3 with a prompt, saves URL to the `images` table
2. **`analyze_image`** — Fetches image from DB, sends to Gemini Vision, caches and returns analysis
3. **`get_project_memory`** — Retrieves all memory entries for the project (called at conversation start)
4. **`save_project_memory`** — Persists a key-value fact to project memory
5. **`get_project_brief`** — Retrieves the project's brief for context
6. **`get_project_images`** — Lists all generated images for the project

The tool loop runs for up to **10 iterations** (safety limit) until Claude returns a final `end_turn` response.

---

## Agent System

### Background Agent (Sub-Agent Pattern)

The background agent implements the **sub-agent pattern**: a separate AI process that runs independently of the main chat flow.

**How it works:**

1. **Trigger**: User calls `POST /projects/{id}/agent/trigger`
2. **Immediate Response**: API creates an `agent_executions` record with `status=pending` and returns the `execution_id` immediately (non-blocking)
3. **Background Processing**: FastAPI's `BackgroundTasks` runs the agent asynchronously:
   - Updates status to `running`
   - Gathers ALL project data (brief, conversations, images, existing memory)
   - Sends everything to Claude with a specialized system prompt
   - Claude organizes the data into structured categories (e.g., `project_overview`, `technical_requirements`, `design_decisions`)
   - Saves each category as a `project_memory` entry with `source=agent`
   - Updates status to `completed` with a result summary
4. **Polling**: Client polls `GET /agent/status/{execution_id}` until status is `completed` or `failed`

**Status Flow:**
```
pending → running → completed
                  → failed (on error)
```

**Memory Categories** the agent extracts:
- `project_overview` — High-level summary
- `project_goals` — Specific objectives
- `technical_requirements` — Tech stack and constraints
- `design_decisions` — Architecture and design choices
- `key_insights` — Important discoveries from conversations
- `action_items` — Outstanding tasks
- `reference_materials` — Important links/resources

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- A [Supabase](https://supabase.com) account
- API keys for: [Anthropic](https://console.anthropic.com), [Google AI](https://ai.google.dev), [OpenAI](https://platform.openai.com)

### 1. Clone the repository
```bash
git clone <repo-url>
cd Project_AI
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up Supabase
1. Create a new project on [supabase.com](https://supabase.com)
2. Go to **SQL Editor** in your Supabase dashboard
3. Copy-paste the contents of `sql/schema.sql` and run it
4. Go to **Settings → API** and copy your Project URL and Anon Key

### 5. Configure environment variables
```bash
cp .env.example .env
# Edit .env and fill in your actual keys
```

---

## Running the Application

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

Interactive API docs (Swagger UI): `http://localhost:8000/docs`

---

## Usage Examples

> **Windows Users:** PowerShell's `curl` is an alias for `Invoke-WebRequest`, which uses different syntax. Use the **PowerShell** examples below, or use the **Swagger UI** at `http://localhost:8000/docs` for a visual interface.

### Create a Project

**Bash (Linux/Mac):**
```bash
curl -X POST http://localhost:8000/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App",
    "brief": {
      "title": "Mobile Fitness App",
      "description": "A fitness tracking app with AI coaching",
      "goals": ["Track workouts", "Provide AI recommendations", "Social features"],
      "reference_links": ["https://example.com/competitor"],
      "target_audience": "Fitness enthusiasts aged 18-35",
      "tech_stack": "React Native, Node.js, PostgreSQL"
    }
  }'
```

**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/projects/" -Method Post -ContentType "application/json" -Body '{"name": "My App", "brief": {"title": "Mobile Fitness App", "description": "A fitness tracking app with AI coaching", "goals": ["Track workouts", "Provide AI recommendations", "Social features"], "reference_links": ["https://example.com/competitor"], "target_audience": "Fitness enthusiasts aged 18-35", "tech_stack": "React Native, Node.js, PostgreSQL"}}'
```

### Chat with Claude

**Bash (Linux/Mac):**
```bash
curl -X POST http://localhost:8000/projects/{project_id}/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the main goals of this project?"}'
```

**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/projects/{project_id}/chat/" -Method Post -ContentType "application/json" -Body '{"message": "What are the main goals of this project?"}'
```

### Generate an Image via Chat

**Bash (Linux/Mac):**
```bash
curl -X POST http://localhost:8000/projects/{project_id}/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Generate a logo concept for this fitness app"}'
```

**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/projects/{project_id}/chat/" -Method Post -ContentType "application/json" -Body '{"message": "Generate a logo concept for this fitness app"}'
```

### Trigger the Background Agent

**Bash (Linux/Mac):**
```bash
curl -X POST http://localhost:8000/projects/{project_id}/agent/trigger

# Poll status
curl http://localhost:8000/agent/status/{execution_id}
```

**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/projects/{project_id}/agent/trigger" -Method Post

# Poll status
Invoke-RestMethod -Uri "http://localhost:8000/agent/status/{execution_id}"
```

### View Project Memory

**Bash (Linux/Mac):**
```bash
curl http://localhost:8000/projects/{project_id}/memory
```

**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/projects/{project_id}/memory"
```

---

## Project Structure

```
Project_AI/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py             # Environment settings
│   ├── database.py           # Supabase client
│   ├── models.py             # Pydantic schemas
│   ├── routers/
│   │   ├── projects.py       # Project CRUD
│   │   ├── chat.py           # Chat + tool loop
│   │   ├── images.py         # Image endpoints
│   │   └── agents.py         # Agent trigger + status
│   ├── services/
│   │   ├── claude_service.py # Claude API + tool orchestration
│   │   ├── gemini_service.py # Gemini Vision analysis
│   │   ├── dalle_service.py  # DALL-E image generation
│   │   ├── memory_service.py # Memory CRUD
│   │   └── agent_service.py  # Background agent logic
│   └── tools/
│       └── tool_definitions.py  # Claude tool schemas
├── sql/
│   └── schema.sql            # Database schema
├── .env.example              # Env template
├── requirements.txt          # Python deps
└── README.md                 # This file
```
