# AI Project Assistant

An AI-powered project assistant built with **FastAPI**, **Claude (Anthropic)**, **Gemini (Google)**, **OpenAI (gpt-image-1)**, and **Supabase**.

## User Flow

1. **Create Project:** User inputs a project brief (title, description, goals) in the UI.
2. **Chat & Iterate:** User chats with the AI to refine the project, generate images, and iterate.
3. **Agent Organization:** A background agent analyzes the conversation and organizes insights into a structured memory.

## Features & Highlights

- **Multi-model Orchestration:** Uses Claude for logic and chat, Gemini for vision analysis, and OpenAI for image generation.
- **Agent Knowledge Organization:** Background agent processes project data into structured memory.
- **Image Generation & Analysis:** Native capabilities to generate images and analyze them.
- **Persistent Project Memory:** Key-value store for facts, decisions, and goals, scoped by project.
- **Interactive UI:** Web-based interface to manage projects, chat with AI, and view generated assets.

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

## Schema Design Decisions

```text
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

- **Decoupled Architecture:** The `projects` table is minimal, acting as the anchor. `project_briefs` is deliberately separated (1:1) to allow independent updates and versioning without touching core project metadata.
- **Key-Value Memory:** `project_memory` uses a key-value strategy instead of free-text, allowing the AI to efficiently query, update, and categorize facts without hallucination.
- **JSONB for Native Arrays:** Arrays like `goals` and `reference_links` are stored directly as JSONB fields to eliminate complex many-to-many tables for simple lists.

## API Endpoints

The API is fully documented via Swagger UI (accessible at `/docs`). Key route groups include:

- `GET/POST /projects/`: CRUD operations for project workspaces and briefs.
- `POST /projects/{id}/chat/`: Drives the conversational tool-loop with Claude.
- `GET /projects/{id}/images/`: Retrieves all generated assets.
- `POST /projects/{id}/agent/trigger`: Executes the background memory organization agent.
- `GET /projects/{id}/memory`: Fetches structured knowledge facts.

## Agent System

The background agent is an asynchronous **sub-agent** that runs independently of the main chat loop.

- **Trigger & Process:** Once triggered, it analyzes the full project brief, chat history, images, and current memory.
- **Structuring:** It synthesizes these inputs into a structured snapshot (e.g., goals, technical specs, user preferences).
- **Persistence:** These insights are updated within `project_memory`, providing the main AI an up-to-date, organized baseline on subsequent chats.

## Setup & Installation

### Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) account (free tier works)
- API keys for: [Anthropic](https://console.anthropic.com), [Google AI](https://ai.google.dev), [OpenAI](https://platform.openai.com)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd Project_AI
   ```
2. **Create a virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up Supabase**
   - Create a new project on [supabase.com](https://supabase.com)
   - Go to **SQL Editor** in your Supabase dashboard
   - Copy-paste the contents of `sql/schema.sql` and run it
   - Go to **Settings → API** and copy your Project URL and Anon Key

### Configuration

Create a `.env` file in the root directory (you can copy `.env.example`). The following environment variables are required:

```env
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-proj-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbG...
```

### Usage

Run the application using Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

Once running, you can access:

- **Web UI**: http://localhost:8000
- **Swagger API Docs**: http://localhost:8000/docs/

## Project Structure

```
Project_AI/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings from .env
│   ├── database.py             # Supabase client singleton
│   ├── models.py               # Pydantic schemas
│   │
│   ├── routers/                # API layer
│   │   ├── projects.py
│   │   ├── chat.py
│   │   ├── images.py
│   │   └── agents.py
│   │
│   ├── services/               # Business logic layer
│   │   ├── claude_service.py
│   │   ├── dalle_service.py
│   │   ├── gemini_service.py
│   │   ├── memory_service.py
│   │   └── agent_service.py
│   │
│   ├── tools/
│   │   └── tool_definitions.py # Claude tool schemas
│   │
│   └── static/                 # Frontend UI
│       ├── index.html
│       ├── css/style.css
│       ├── js/api.js
│       ├── js/app.js
│       └── uploads/            # Generated images locally
│
├── sql/
│   └── schema.sql              # Database schema
├── .env.example                # Env template
├── requirements.txt            # Dependencies
└── README.md                   # This file
```
