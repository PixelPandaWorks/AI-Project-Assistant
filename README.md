# AI Project Assistant

An AI-powered project assistant built with **FastAPI**, **Claude (Anthropic)**, **Gemini (Google)**, **OpenAI (gpt-image-1)**, and **Supabase**. Users can create projects, chat with an AI assistant that has access to tools, generate and analyze images, persist project knowledge via memory, and trigger a background agent that organizes all project data into structured memory files.

A web-based UI is included for interacting with the system.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Schema Design Decisions](#schema-design-decisions)
- [API Endpoints](#api-endpoints)
- [Tool Loop (Chat → Tools → Response)](#tool-loop-chat--tools--response)
- [Agent System (Sub-Agent Pattern)](#agent-system-sub-agent-pattern)
- [Code Structure](#code-structure)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Usage Examples](#usage-examples)

---

## Architecture Overview

```
┌──────────────────┐     ┌──────────────────────────────────────────┐
│   Web UI         │────▶│            FastAPI Backend               │
│  (HTML/JS/CSS)   │◀────│                                          │
└──────────────────┘     │  ┌─────────┐  ┌────────┐  ┌──────────┐  │
                         │  │ Routers │──│Services│──│  Tools   │  │
                         │  └─────────┘  └────────┘  └──────────┘  │
                         │       │            │            │         │
                         │       ▼            ▼            ▼         │
                         │  ┌─────────┐  ┌────────┐  ┌──────────┐  │
                         │  │Supabase │  │ Claude │  │  OpenAI  │  │
                         │  │  (DB)   │  │  API   │  │gpt-image │  │
                         │  └─────────┘  └────────┘  └──────────┘  │
                         │                    │                      │
                         │               ┌────────┐                 │
                         │               │ Gemini │                 │
                         │               │ Vision │                 │
                         │               └────────┘                 │
                         └──────────────────────────────────────────┘
```

### Tech Stack
| Component | Technology | Purpose |
|-----------|------------|---------|
| Runtime | Python 3.11+ | Core language |
| Web Framework | FastAPI | Async REST API with auto-generated docs |
| Primary AI | Anthropic Claude | Chat, reasoning, tool orchestration |
| Image Analysis | Google Gemini (Vision) | Analyzing generated images |
| Image Generation | OpenAI gpt-image-1 | Creating images from text prompts |
| Database | Supabase (PostgreSQL) | Data persistence |
| Frontend | Vanilla HTML/CSS/JS | Web UI for interacting with the system |

---

## Schema Design Decisions

### Entity-Relationship Overview

```
projects (1) ─────── (1) project_briefs
    │
    ├──── (many) conversations
    │
    ├──── (many) images
    │
    ├──── (many) project_memory
    │
    └──── (many) agent_executions
```

### Tables & Design Rationale

| Table | Purpose | Key Design Decision |
|-------|---------|---------------------|
| `projects` | Top-level entity | Intentionally minimal (just `id` + `name`). Acts as the anchor for all other entities via foreign keys. |
| `project_briefs` | Project definition document | **Separated from `projects` (1:1 via unique FK)** rather than embedding fields directly. This allows independent updates to the brief without touching the project entity, and supports future versioning or draft workflows. |
| `conversations` | Chat message history | Stores both `user` and `assistant` messages with role-based filtering. The `tool_calls` JSONB column preserves the full tool invocation chain for debugging and audit trails. |
| `images` | Generated images | Links to project via FK. The `analysis` column **caches Gemini's vision output** so analyzing the same image twice doesn't cost extra API credits. |
| `project_memory` | Persistent knowledge store | **Key-value design** (not free-text) enables targeted retrieval and updates. The `source` field tracks origin (`user`, `assistant`, or `agent`). A composite unique index on `(project_id, memory_key)` prevents duplicate keys per project. |
| `agent_executions` | Background job tracking | Tracks the full lifecycle: `pending → running → completed/failed`. The `task_type` field future-proofs for multiple agent types. `result` JSONB stores structured outcomes. |

### Why JSONB for goals and reference_links?

PostgreSQL's JSONB allows flexible array storage without needing separate join tables and many-to-many relationships. For simple lists of strings (goals, links), JSONB is queryable, indexable, and avoids unnecessary schema complexity.

### Why separate `project_briefs` from `projects`?

Decoupling follows the **Single Responsibility Principle** — the project entity manages identity/ownership, while the brief manages project definition. This supports:
- Independent brief updates without touching the project row
- Future features like brief versioning, approval workflows, or multiple drafts
- Cleaner API design (`PUT /projects/{id}/brief` vs mixing fields)

### Why key-value memory instead of free-text?

Key-value memory (`memory_key` → `memory_value` as JSONB) allows Claude to:
1. **Retrieve specific facts** quickly (e.g., "preferred_color_scheme")
2. **Update individual entries** without rewriting everything (upsert by key)
3. **Categorize information** naturally (the key serves as the category)
4. **Distinguish sources** — memory from the user, the assistant, or the background agent

### Full Schema

The complete SQL schema is at [`sql/schema.sql`](sql/schema.sql). Key features:
- UUID primary keys (auto-generated via `uuid-ossp`)
- `ON DELETE CASCADE` on all foreign keys — deleting a project removes all related data
- `CHECK` constraints on `role`, `status`, and `source` fields for data integrity
- Indexes on foreign keys and common query patterns

---

## API Endpoints

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/` | Create a new project with a brief |
| `GET` | `/projects/` | List all projects with their briefs |
| `GET` | `/projects/{id}` | Get a project with its brief |
| `PUT` | `/projects/{id}/brief` | Update a project's brief |

### Chat (Tool Loop)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{id}/chat/` | Send a message → Claude processes with full tool loop → returns response |
| `GET` | `/projects/{id}/chat/` | Get full conversation history for a project |

### Images
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects/{id}/images/` | List all images generated for a project |
| `GET` | `/projects/{id}/images/{image_id}` | Get a specific image |

### Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{id}/agent/trigger` | Trigger the background knowledge-organization agent |
| `GET` | `/agent/status/{execution_id}` | Poll agent execution status |

### Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects/{id}/memory` | View all stored memory entries for a project |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the web UI (or health check if UI not built) |
| `GET` | `/health` | Detailed health check — shows which services are connected |

---

## Tool Loop (Chat → Tools → Response)

The core chat endpoint implements a **complete tool-calling loop** where Claude can invoke tools, receive results, and continue reasoning until it produces a final answer.

### Flow

```
User sends message
       │
       ▼
┌─ Load last 50 messages from DB ──────────────────┐
│  Save user message to DB                          │
│  Build messages array with history                │
└───────────────────────────────────────────────────┘
       │
       ▼
┌─ TOOL LOOP (max 10 iterations) ──────────────────┐
│                                                    │
│  Send messages + tool definitions to Claude        │
│       │                                            │
│       ▼                                            │
│  Claude responds with stop_reason:                 │
│                                                    │
│  ├── "end_turn" → Extract text → DONE             │
│  │                                                 │
│  └── "tool_use" → For each tool_use block:        │
│       │                                            │
│       ├── Route to service handler                 │
│       ├── Execute tool (generate image, etc.)      │
│       ├── Log the tool call                        │
│       ├── Feed result back to Claude               │
│       └── Continue loop                            │
│                                                    │
└────────────────────────────────────────────────────┘
       │
       ▼
Save assistant response to DB
Return { response, tool_calls, images_generated }
```

### Available Tools (6 total)

| Tool | Service | API Used | What It Does |
|------|---------|----------|--------------|
| `generate_image` | `dalle_service` | OpenAI gpt-image-1 | Generates an image from a text prompt, saves locally + DB |
| `analyze_image` | `gemini_service` | Google Gemini Vision | Downloads image, sends to Gemini for visual analysis, caches result |
| `get_project_memory` | `memory_service` | Supabase | Retrieves all memory entries (called at conversation start) |
| `save_project_memory` | `memory_service` | Supabase | Persists a key-value fact to project memory |
| `get_project_brief` | direct DB query | Supabase | Retrieves the project's brief for context |
| `get_project_images` | direct DB query | Supabase | Lists all generated images for the project |

### Key Implementation Details

- **History loading**: The last 50 messages are loaded from the database to maintain conversational context
- **Safety limit**: Tool loop capped at 10 iterations to prevent infinite loops
- **Result truncation**: Tool results over 5,000 characters are truncated to avoid context overflow
- **Persistent storage**: Both user and assistant messages (including tool call metadata) are saved to the database
- **Multi-tool support**: Claude can invoke multiple tools in a single turn — all are processed and fed back before the next iteration

### Multi-Model Orchestration

The system uses **three different AI models** working together:
1. **Claude** (Anthropic) — Primary reasoning and chat, decides when and which tools to use
2. **gpt-image-1** (OpenAI) — Called by Claude via `generate_image` tool to create images
3. **Gemini Vision** (Google) — Called by Claude via `analyze_image` tool to understand images

Claude acts as the **orchestrator** — it decides based on the user's message whether to generate images, analyze them, save/retrieve memory, or simply respond with text.

---

## Agent System (Sub-Agent Pattern)

### What is the Background Agent?

The background agent is a **sub-agent** — a separate AI process that runs independently of the main chat flow. While the chat tool loop is synchronous (user waits for response), the background agent runs **asynchronously** and can be polled for status.

### How It Works

```
1. TRIGGER                          2. BACKGROUND PROCESSING
   POST /projects/{id}/agent/trigger    ┌──────────────────────────┐
        │                               │ Status: pending → running│
        ▼                               │                          │
   Create execution record              │ Gather ALL project data: │
   Return execution_id immediately      │  ├── Project brief       │
        │                               │  ├── Conversations       │
        │                               │  ├── Images + analyses   │
        │                               │  └── Existing memory     │
        │                               │                          │
        │                               │ Send to Claude with      │
        │                               │ structuring prompt        │
        │                               │                          │
        │                               │ Claude returns:          │
        │                               │  structured JSON array   │
3. POLL                                 │  of memory entries       │
   GET /agent/status/{exec_id}          │                          │
        │                               │ Save each entry to       │
        ▼                               │ project_memory table     │
   Returns current status:              │ (source = "agent")       │
   pending / running /                  │                          │
   completed / failed                   │ Status: → completed      │
                                        └──────────────────────────┘
```

### Agent vs Chat (Sub-Agent Pattern)

| Aspect | Chat (Main Agent) | Background Agent (Sub-Agent) |
|--------|-------------------|------------------------------|
| Trigger | User sends a message | API endpoint call |
| Execution | Synchronous (user waits) | Asynchronous (non-blocking) |
| Tools | 6 tools (generate, analyze, memory, etc.) | No tools — single Claude call |
| Purpose | Respond to user queries | Organize project knowledge |
| System Prompt | General assistant | Specialized knowledge organizer |
| Output | Text response to user | Structured memory entries |
| Status Tracking | N/A | `agent_executions` table (pending → running → completed/failed) |

### Memory Categories the Agent Extracts

The agent analyzes all project data and organizes it into categories like:
- `project_overview` — High-level summary of the project
- `project_goals` — Specific objectives
- `technical_requirements` — Tech stack, integrations, constraints
- `design_decisions` — Architecture and design choices made
- `key_insights` — Important discoveries from conversations
- `action_items` — Outstanding tasks and next steps
- `reference_materials` — Important links and resources
- `team_preferences` — Preferences expressed during conversations

These are saved to `project_memory` with `source = "agent"`, distinguishable from user or assistant memory entries.

---

## Code Structure

```
Project_AI/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app — lifespan, CORS, static files, router mounting
│   ├── config.py               # Settings from .env (API keys, model names)
│   ├── database.py             # Supabase client singleton
│   ├── models.py               # Pydantic request/response schemas
│   │
│   ├── routers/                # API layer (thin — delegates to services)
│   │   ├── projects.py         #   Project CRUD
│   │   ├── chat.py             #   Chat endpoint (delegates to claude_service)
│   │   ├── images.py           #   Image listing endpoints
│   │   └── agents.py           #   Agent trigger + status polling + memory listing
│   │
│   ├── services/               # Business logic layer
│   │   ├── claude_service.py   #   Tool loop orchestrator (core chat logic)
│   │   ├── dalle_service.py    #   OpenAI image generation
│   │   ├── gemini_service.py   #   Gemini Vision image analysis
│   │   ├── memory_service.py   #   Memory CRUD (upsert by key)
│   │   └── agent_service.py    #   Background agent logic
│   │
│   ├── tools/
│   │   └── tool_definitions.py #   Claude tool schemas (Anthropic format)
│   │
│   └── static/                 # Frontend UI
│       ├── index.html          #   Main SPA page
│       ├── css/style.css       #   Glassmorphism dark theme
│       ├── js/api.js           #   API client wrapper
│       ├── js/app.js           #   UI logic (chat, projects, memory, images)
│       └── uploads/            #   Generated images saved locally
│
├── sql/
│   └── schema.sql              # Database schema (run in Supabase SQL Editor)
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

### Design Principles
- **Layered architecture**: Routers (thin) → Services (logic) → External APIs
- **Single Responsibility**: Each service handles one concern (Claude, DALL-E, Gemini, Memory, Agent)
- **Configuration centralized**: All API keys and model names in `config.py`
- **Frontend served by backend**: Static files mounted at `/static`, SPA served at `/`

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- A [Supabase](https://supabase.com) account (free tier works)
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
# Edit .env and fill in your actual API keys
```

Required variables:
```
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-proj-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbG...
```

---

## Running the Application

```bash
uvicorn app.main:app --reload --port 8000
```

- **Web UI**: http://localhost:8000
- **Swagger API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## Usage Examples

> **Note:** You can also use the web UI at `http://localhost:8000` for a visual interface instead of CLI commands.

### Create a Project

**Bash:**
```bash
curl -X POST http://localhost:8000/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App",
    "brief": {
      "title": "Mobile Fitness App",
      "description": "A fitness tracking app with AI coaching",
      "goals": ["Track workouts", "AI recommendations"],
      "reference_links": [],
      "target_audience": "Fitness enthusiasts aged 18-35",
      "tech_stack": "React Native, Node.js, PostgreSQL"
    }
  }'
```

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/projects/" -Method Post `
  -ContentType "application/json" `
  -Body '{"name": "My App", "brief": {"title": "Mobile Fitness App", "description": "A fitness tracking app", "goals": ["Track workouts"], "reference_links": [], "target_audience": "Fitness enthusiasts", "tech_stack": "React Native"}}'
```

### Chat with Claude
```bash
curl -X POST http://localhost:8000/projects/{project_id}/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the main goals of this project?"}'
```

### Generate an Image via Chat
```bash
curl -X POST http://localhost:8000/projects/{project_id}/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Generate a logo concept for this fitness app"}'
```

### Trigger the Background Agent
```bash
# Trigger
curl -X POST http://localhost:8000/projects/{project_id}/agent/trigger

# Poll status
curl http://localhost:8000/agent/status/{execution_id}
```

### View Project Memory
```bash
curl http://localhost:8000/projects/{project_id}/memory
```
