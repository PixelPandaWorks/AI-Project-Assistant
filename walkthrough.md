# AI Project Assistant — Walkthrough

## What Was Built

The entire backend for the AI Project Assistant is now complete. Here's what was created:

### Files Created (18 files)

| File | Purpose |
|------|---------|
| [requirements.txt](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/requirements.txt) | Python dependencies (FastAPI, Anthropic, Gemini, OpenAI, Supabase) |
| [.env.example](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/.env.example) | Template for environment variables |
| [.gitignore](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/.gitignore) | Git ignore rules |
| [sql/schema.sql](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/sql/schema.sql) | Full database schema (6 tables, indexes, constraints) |
| [app/config.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/config.py) | Settings loaded from .env |
| [app/database.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/database.py) | Supabase client singleton |
| [app/models.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/models.py) | Pydantic request/response models |
| [app/main.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/main.py) | FastAPI app entry point |
| [app/tools/tool_definitions.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/tools/tool_definitions.py) | 6 tool schemas for Claude |
| [app/services/claude_service.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/services/claude_service.py) | Claude API integration with full tool loop |
| [app/services/gemini_service.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/services/gemini_service.py) | Gemini Vision image analysis |
| [app/services/dalle_service.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/services/dalle_service.py) | DALL-E 3 image generation |
| [app/services/memory_service.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/services/memory_service.py) | Memory CRUD operations |
| [app/services/agent_service.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/services/agent_service.py) | Background agent logic |
| [app/routers/projects.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/routers/projects.py) | Project CRUD endpoints |
| [app/routers/chat.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/routers/chat.py) | Chat endpoint with tool loop |
| [app/routers/images.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/routers/images.py) | Image listing endpoints |
| [app/routers/agents.py](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/app/routers/agents.py) | Agent trigger & status polling |
| [README.md](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/README.md) | Full documentation |

### Validation
- ✅ Virtual environment created (`venv/`)
- ✅ All dependencies installed via pip
- ✅ Import validation passed — config, models, and tool definitions all load correctly

---

## Your Next Steps

> [!IMPORTANT]
> You need to complete 3 steps before you can run the server.

### Step 1: Create your `.env` file

Create a file called `.env` in the project root (`c:\Users\bmwag\Desktop\VS Code\Project_AI\.env`) with your actual API keys:

```
ANTHROPIC_API_KEY=sk-ant-your-actual-key
GEMINI_API_KEY=your-actual-gemini-key
OPENAI_API_KEY=sk-your-actual-openai-key
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key
```

### Step 2: Run the SQL schema in Supabase

1. Log in to [supabase.com](https://supabase.com) and open your project
2. Click **SQL Editor** in the left sidebar
3. Click **New Query**
4. Copy the entire contents of [sql/schema.sql](file:///c:/Users/bmwag/Desktop/VS%20Code/Project_AI/sql/schema.sql) and paste it into the editor
5. Click **Run** — you should see "Success" with no errors

### Step 3: Start the server

Open a terminal in the project folder and run:

```bash
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Then open **http://localhost:8000/docs** in your browser to see the interactive Swagger UI.

---

## How to Test

Once the server is running, try these in order:

**1. Health check:**
```bash
curl http://localhost:8000/health
```

**2. Create a project:**
```bash
curl -X POST http://localhost:8000/projects/ -H "Content-Type: application/json" -d "{\"name\": \"Test Project\", \"brief\": {\"title\": \"My First Project\", \"description\": \"A test project\", \"goals\": [\"Test the API\"], \"reference_links\": []}}"
```

**3. Chat with Claude** (use the project ID from step 2):
```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/chat/ -H "Content-Type: application/json" -d "{\"message\": \"Hello! What can you help me with?\"}"
```

**4. Trigger the background agent:**
```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/agent/trigger
```

**5. Poll agent status** (use the execution_id from step 4):
```bash
curl http://localhost:8000/agent/status/{EXECUTION_ID}
```

---

## Key Architecture Highlights

### Tool Loop (claude_service.py)
The core of the system. Claude receives 6 tools and can invoke them in a loop (up to 10 iterations). Each tool call is routed to the appropriate service, executed, and the result is fed back to Claude until it produces a final text response.

### Background Agent (agent_service.py)
Implements the sub-agent pattern. Triggered via API, runs asynchronously via `BackgroundTasks`, gathers all project data, sends to Claude for structuring, and saves organized memory entries. Full status tracking (pending → running → completed/failed).

### Memory System (memory_service.py)
Key-value storage scoped per project. Claude checks memory at conversation start and saves important facts as it goes. The background agent also writes structured memory. All entries track their source (`user`, `assistant`, or `agent`).
