# SocietyBoard AI

An AI-powered management platform for co-op housing societies — combining a
FastAPI + PostgreSQL backend, a React admin dashboard, a WhatsApp bot, and a
provider-agnostic multi-agent AI layer (chat agents, an MCP tool server, and
an autonomous workflow planner) behind one shared service layer.

## Overview

Co-op housing societies routinely run on manual, ad-hoc coordination:
residents don't know when water is available, committees track vendor
assignments in group chats, and requests like "who's the plumber for this
building" or "what's our current occupancy" have no single source of truth.

SocietyBoard AI gives a society one shared backend for that data (buildings,
flats, residents, vendors, water schedules, service requests) and exposes it
through four different interfaces built on the exact same service layer:
a REST API for the admin dashboard, a WhatsApp bot for residents, a chat-based
AI Assistant (with separate resident- and committee-scoped agents) for
natural-language queries, and an MCP tool server for external AI clients.
On top of that, an autonomous WorkflowAgent can plan and execute multi-step
operational tasks (e.g. "assign an available plumber to every open plumbing
request") end to end.

## Key Features

- **REST API** for buildings, flats, residents, vendors, water schedules, and
  service requests, backed by PostgreSQL
- **React admin dashboard** — occupancy directory, water schedule editor,
  vendor management, service request tracking with vendor assignment, and a
  home page with live society-wide statistics
- **WhatsApp bot** (Twilio) — resident self-service: water timings, flat
  status, logging complaints, with phone-number-based onboarding
- **AI Assistant chat** — two role-scoped agents (Resident, Committee) behind
  one endpoint, using a provider-agnostic JSON-action tool-calling loop
- **MCP server** — a from-scratch, standard-library-only implementation of
  the Model Context Protocol, exposing 8 tools over the stdio transport for
  external AI clients (Claude Desktop, MCP Inspector, etc.)
- **Autonomous workflow execution** — given a goal, an agent plans an ordered
  sequence of tool calls, executes them against the real database, and
  reports what happened, all synchronously in one request
- **Local-first LLM** via Ollama by default, with a provider abstraction that
  also supports Anthropic's Claude — switching providers is a config change,
  not a code change

## AI Architecture

Every AI-facing feature — WhatsApp, the AI Assistant, the MCP server, and
WorkflowAgent — is built on the same small set of abstractions:

- **`LLMProvider`** (`services/llm/base.py`): a minimal interface
  (`chat(messages) -> LLMResponse`) implemented by `OllamaProvider` (default)
  and `ClaudeProvider`. Nothing above this layer knows which one is active.
- **JSON-action tool loop** (`services/agent/base_agent.py`): rather than
  relying on any one provider's native tool-calling format (which varies by
  provider and, for local models, by version), the agent instructs the model
  via its system prompt to always respond with a JSON object — either a tool
  call or a final answer — and parses that itself. This is what makes the
  same loop work identically against Ollama or Claude with zero
  provider-specific branching.
- **Resident Agent** (`services/agent/resident_agent.py`): the tools WhatsApp
  and the AI Assistant's default mode use — `get_water_schedule`,
  `get_flat_status`, `log_service_request`. `log_service_request` always
  writes against the caller-supplied resident (resolved from the WhatsApp
  phone number); its function signature has no `resident_id`/`flat_id`
  parameter at all, so a model cannot supply one to impersonate someone else.
- **Committee Agent** (`services/agent/committee_agent.py`): a distinct,
  broader read/aggregate tool set for committee members —
  `list_buildings`, `list_vendors`, `list_service_requests`,
  `search_residents`, `dashboard_summary`. It does not have
  `log_service_request` or any other resident-write tool.
- **Agent factory** (`services/agent/factory.py`): `get_agent(role, provider)`
  is the single place that constructs the right agent for a role. An
  unrecognized role falls back to the more restrictive resident role.
- **MCP server** (`app/mcp_server.py` + `app/mcp_protocol.py`): a fourth,
  independent entry point — it does not depend on ResidentAgent or
  CommitteeAgent, and calls `services/core/` functions directly.
- **WorkflowAgent** (`services/agent/workflow_agent.py`): also independent of
  the chat agents — it has its own tool set (`workflow_tools.py`) built from
  `services/core/`, and its own plan/execute/report loop.

```mermaid
graph TD
    WA[WhatsApp Webhook] --> Factory
    Assistant["AI Assistant API<br/>(/assistant/chat)"] --> Factory
    Factory["Agent Factory<br/>get_agent(role)"] --> RA[Resident Agent]
    Factory --> CA[Committee Agent]
    RA --> Base[BaseAgent<br/>JSON-action loop]
    CA --> Base
    Base --> Provider[LLMProvider]
    Provider --> Ollama[Ollama]
    Provider --> Claude[Claude]

    RA -- resident tools --> ResTools["get_water_schedule<br/>get_flat_status<br/>log_service_request"]
    CA -- committee tools --> ComTools["list_buildings<br/>list_vendors<br/>list_service_requests<br/>search_residents<br/>dashboard_summary"]

    WF[WorkflowAgent] --> Base
    WF -- workflow tools --> Core

    ResTools --> Core[services/core/]
    ComTools --> Core
    MCP[MCP Server] --> Core
    REST[REST API routes] --> Core
    Core --> DB[(PostgreSQL)]
```

## MCP Architecture

The MCP server is a **from-scratch, standard-library-only implementation**
of the Model Context Protocol (`app/mcp_protocol.py`) — it does **not** use
the official `mcp` Python SDK, whose pinned dependencies conflicted with this
project's FastAPI/Pydantic versions. It implements JSON-RPC 2.0 over the
stdio transport (newline-delimited JSON, one message per line), supporting
`initialize`, `tools/list`, `tools/call`, and `ping`, with standard JSON-RPC
error codes for malformed requests and a protocol-level `isError` result
(not a JSON-RPC error) for a failed tool call.

It exists as a **fourth entry point**, parallel to REST, WhatsApp, and the
AI Assistant — all reuse the exact same `services/core/` functions rather
than each implementing their own queries.

**Implemented MCP tools (8):**

| Tool | Description |
|---|---|
| `get_water_schedule` | Today's corporation/bore water timing |
| `get_flat_status` | Occupancy status for a specific flat |
| `search_residents` | Search residents by name or phone number |
| `list_buildings` | List every building, including bore-water availability |
| `list_vendors` | List vendors, optionally filtered by category/active status |
| `list_service_requests` | List service requests, optionally filtered by status |
| `create_service_request` | File a new request for a flat (building name + flat number) |
| `dashboard_summary` | Aggregate occupancy, vendor, and request-status statistics |

```mermaid
graph TD
    Clients["Frontend / External AI Clients<br/>(Claude Desktop, MCP Inspector)"] --> MCP["MCP Server<br/>(app/mcp_server.py + mcp_protocol.py)"]
    MCP --> Core["Shared Service Layer<br/>(services/core/)"]
    REST["REST API<br/>(api/routes/)"] --> Core
    Agents["Resident / Committee Agents"] --> Core
    WF["WorkflowAgent"] --> Core
    Core --> PG[(PostgreSQL)]
```

## Multi-Agent Architecture

The **Resident Assistant** and **Committee Assistant** are two distinct
agent instances — not two copies of the same prompt with a different label.
They differ in both system prompt and, more importantly, in the literal
`tool_registry` each one is constructed with:

| | Resident Agent | Committee Agent |
|---|---|---|
| Scope | A single resident's own flat | Society-wide |
| Tools | `get_water_schedule`, `get_flat_status`, `log_service_request` | `list_buildings`, `list_vendors`, `list_service_requests`, `search_residents`, `dashboard_summary` |
| Can write data? | Yes — logs a service request for the caller's own flat | No — read/aggregate only |
| Used by | WhatsApp (always), AI Assistant (default) | AI Assistant (`role: "committee"`) |

The AI Assistant's `POST /api/v1/assistant/chat` endpoint accepts an
optional `role` field (`"resident"` default, or `"committee"`); WhatsApp is
hardcoded to the resident role with no way to select committee. Both agents
run through the identical `BaseAgent` loop — role separation is enforced by
which tools are actually passed in at construction time, not by asking the
model to self-restrict.

## Autonomous Workflow Architecture

`WorkflowAgent` (`services/agent/workflow_agent.py`) is a **planner/executor**,
distinct from the reactive chat agents above:

```text
Goal → LLM Planning (one call, produces an ordered JSON step list)
     → Execute each step against the real database, in order
     → Collect a status ("done"/"error") + result per step
     → LLM Final Report (one call, plain-language summary of what happened)
```

Execution is **synchronous and bounded** — the entire plan runs inside one
HTTP request/response, capped at a fixed maximum step count (8 by default)
so a runaway plan can't execute indefinitely. There is **no background job
queue, no streaming progress, and no persisted workflow history** — each run
is stateless; the full trace is returned once, in the response.

**Example** — goal: *"Assign an available plumber to every open plumbing
request"*

1. Plan: `list_service_requests(status="open")` → `find_available_vendor(category="Plumber")` → `assign_vendor_to_request(...)` for each matching request
2. Execute: each step runs for real against PostgreSQL, updating `service_requests` rows
3. Report: *"Assigned Ganesh Pipe Works to 2 open plumbing requests, scheduled for tomorrow morning."*

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI 0.115 |
| ORM / migrations | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL 16 |
| LLM (default) | Ollama (local, e.g. `llama3.1`) |
| LLM (alternative) | Anthropic Claude (`anthropic` SDK) |
| MCP | Custom JSON-RPC/stdio implementation (standard library only) |
| WhatsApp | Twilio |
| Frontend | React 19 + Vite + React Router 7 |
| Styling | Tailwind CSS 4 |
| HTTP client | Axios |
| Backend testing | pytest, sqlite (in-memory, for unit/service tests) |
| Frontend testing | Vitest + React Testing Library |

## Project Structure

```text
backend/
  app/
    api/routes/          # REST routes: buildings, flats, residents, vendors,
                          # water_schedule, service_requests, whatsapp,
                          # assistant, workflows
    models/               # SQLAlchemy models (one file per table)
    schemas/               # Pydantic request/response schemas
    services/
      core/                # Framework-free service functions (shared by
                            # REST routes, agents, and MCP tools)
      agent/
        base_agent.py       # Shared JSON-action tool-calling loop
        resident_agent.py   # Resident-scoped agent + tool list
        committee_agent.py  # Committee-scoped agent
        committee_tools.py  # Committee tool wrappers over services/core/
        tools.py             # Resident tool wrappers (water/flat/log request)
        factory.py            # get_agent(role, provider)
        workflow_agent.py      # Autonomous plan/execute/report agent
        workflow_tools.py       # WorkflowAgent's tool set
      llm/                   # LLMProvider, OllamaProvider, ClaudeProvider
      whatsapp/                # Onboarding + Twilio client
    mcp_protocol.py            # Standalone JSON-RPC/MCP protocol implementation
    mcp_server.py                # MCP tool registrations (entry point)
    main.py                       # FastAPI app, router mounts, /health
    database.py                    # Engine, session, session_scope()
    config.py                       # Settings (env-driven)
  alembic/                          # Migrations
  tests/                             # pytest suite (122 tests)

frontend/
  src/
    api/                   # One module per resource (axios wrappers)
    components/            # Layout, Sidebar, Topbar, shared UI primitives
    pages/                  # DashboardHomePage, WaterSchedulePage,
                            # BuildingsPage, VendorsPage, ResidentsPage,
                            # ServiceRequestsPage, AIAssistantPage,
                            # WorkflowsPage
    App.jsx                 # Route table
```

## Database

PostgreSQL, 6 tables, managed via Alembic:

| Table | Key columns | Relationships |
|---|---|---|
| `buildings` | `name` (unique), `has_bore_water` | has many `flats` |
| `flats` | `building_id`, `flat_number`, `status` (enum: unknown/owner/rented/vacant) | belongs to `buildings`; has many `residents`, `service_requests`; unique on `(building_id, flat_number)` |
| `residents` | `flat_id`, `name`, `phone_number` (unique), `role` (owner/tenant), `onboarded_at` | belongs to `flats`; has many `service_requests` |
| `vendors` | `name`, `category`, `phone_number`, `is_active` | referenced by `service_requests` |
| `water_schedules` | `source` (unique: corporation/bore), `start_time`, `end_time`, `note`, `updated_by` | standalone |
| `service_requests` | `flat_id`, `requested_by_id` (nullable), `category`, `description`, `status` (open/assigned/done), `vendor_id` (nullable), `assigned_slot` | belongs to `flats`, `residents`, `vendors` |

## Getting Started

Instructions below are for **Windows PowerShell**.

### 1. Clone the repository

```powershell
git clone <your-repository-url>
cd societyboard-ai
```

### 2. Backend: create and activate a virtual environment

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Then open `.env` and adjust values as needed (see [Environment Variables](#environment-variables) below). Defaults work for local development as-is.

### 5. Start PostgreSQL

Using Docker (recommended):

```powershell
cd ..
docker-compose up postgres -d
```

Or point `DATABASE_URL` in `.env` at your own local PostgreSQL instance.

Apply migrations:

```powershell
cd backend
alembic upgrade head
```

### 6. Verify Ollama is running

```powershell
ollama pull llama3.1
ollama serve
```

In another terminal, confirm it's reachable:

```powershell
curl http://localhost:11434
```

### 7. Start the FastAPI backend

```powershell
cd backend
uvicorn app.main:app --reload
```

Verify:

```powershell
curl http://localhost:8000/health
```

### 8. Start the React frontend

```powershell
cd ..\frontend
npm install
npm run dev
```

Visit `http://localhost:5173`.

## Environment Variables

All read from `backend/.env` (see `backend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://societyboard:societyboard@localhost:5432/societyboard` | PostgreSQL connection string |
| `ENVIRONMENT` | `development` | Reported by `/health` |
| `API_V1_PREFIX` | `/api/v1` | REST route prefix |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `LLM_PROVIDER` | `ollama` | `ollama` or `claude` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama server |
| `OLLAMA_MODEL` | `llama3.1` | Model name to use |
| `ANTHROPIC_API_KEY` | *(blank)* | Required only if `LLM_PROVIDER=claude` |
| `OPENAI_API_KEY` | *(blank)* | Reserved — no OpenAI provider is implemented yet |
| `GEMINI_API_KEY` | *(blank)* | Reserved — no Gemini provider is implemented yet |
| `TWILIO_ACCOUNT_SID` | *(blank)* | Required for outbound WhatsApp sends via the REST client (not required for the webhook's own TwiML replies) |
| `TWILIO_AUTH_TOKEN` | *(blank)* | Twilio auth token |
| `TWILIO_WHATSAPP_NUMBER` | `whatsapp:+14155238886` | Twilio Sandbox default number |

**Never commit a real `.env` file or real credentials.** Use `.env.example` as the template; all values above are placeholders.

## Running Tests

Backend:

```powershell
cd backend
pytest
```

At the time of writing, this runs **122 tests, all passing**, covering
models/services, REST routes, the LLM provider abstraction, both chat
agents, the agent factory, the MCP protocol implementation and its tools,
WorkflowAgent, and the WhatsApp webhook. Success looks like `122 passed`
with no failures or errors; a `StarletteDeprecationWarning` about `httpx`
in `TestClient` may appear and is harmless.

Frontend:

```powershell
cd frontend
npm test
```

This runs **39 tests across 5 files**, all passing.

## API

Base path: `/api/v1`. Key endpoints (see `/docs` for the full interactive
OpenAPI schema once the server is running):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/buildings` | List buildings |
| `POST` | `/buildings` | Create a building |
| `GET` | `/flats` | List flats (optional `building_id` filter) |
| `PATCH` | `/flats/{id}` | Update a flat's occupancy status |
| `GET` | `/residents` | List residents |
| `GET` | `/residents/by-phone/{phone}` | Look up a resident by phone number |
| `GET` | `/vendors` | List vendors (optional `category`, `active_only`) |
| `PATCH` | `/vendors/{id}` | Update a vendor (e.g. activate/deactivate) |
| `GET` | `/water-schedule` | List current water timings |
| `PUT` | `/water-schedule/{source}` | Set/update timing for a source |
| `GET` | `/service-requests` | List service requests (optional `status`) |
| `POST` | `/service-requests` | Log a new request |
| `PATCH` | `/service-requests/{id}` | Assign a vendor/slot or mark done |
| `POST` | `/whatsapp/webhook` | Twilio webhook (form-encoded, returns TwiML) |
| `POST` | `/assistant/chat` | AI Assistant chat (`message`, optional `role`) |
| `POST` | `/workflows/run` | Run an autonomous workflow (`goal`) |

`GET /health` (outside `/api/v1`) reports API status, database connectivity, and the active LLM provider.

## MCP Usage

Run the MCP server (stdio transport):

```powershell
cd backend
python -m app.mcp_server
```

Test it with the official MCP Inspector (a separate Node.js tool — it
speaks the protocol independently of this project's Python implementation):

```powershell
npx @modelcontextprotocol/inspector python -m app.mcp_server
```

This opens a browser UI where you can call `tools/list` and then invoke any
of the 8 tools (e.g. `list_buildings` with no arguments, or
`get_water_schedule` with `source: bore`) and see live results from your
actual database.

To connect Claude Desktop, add to its config:

```json
{
  "mcpServers": {
    "societyboard-ai": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "C:\\absolute\\path\\to\\societyboard-ai\\backend"
    }
  }
}
```

## Screenshots

*(Add screenshots here as the project is deployed/demoed — no images are
committed to the repository yet.)*

- `docs/screenshots/dashboard.png` — Dashboard home with occupancy and service request statistics
- `docs/screenshots/assistant.png` — AI Assistant chat, showing the Resident/Committee toggle
- `docs/screenshots/workflows.png` — A completed autonomous workflow run with its step trace

## Design Decisions

- **LLM provider abstraction**: `LLMProvider` is a two-method interface so
  the entire agent layer is indifferent to Ollama vs. Claude. The
  JSON-action tool protocol (rather than each provider's native tool-calling
  format) is what makes this genuinely provider-agnostic instead of
  Ollama-only in practice.
- **Shared `services/core/` layer**: every read/write operation exists once,
  as a plain function taking a `Session`. REST routes, MCP tools, and agent
  tools all call the same functions — none of them re-implement a query.
- **MCP as its own protocol boundary**: the MCP server never imports
  `ResidentAgent`/`CommitteeAgent`, and the chat agents never import the MCP
  server. Both are independent consumers of `services/core/`, which keeps
  MCP usable by any future agent (including a future multi-agent system)
  without coupling to this project's specific chat UX.
- **Custom MCP implementation over the official SDK**: the official `mcp`
  Python SDK's pinned dependencies conflicted with this project's
  FastAPI/Pydantic versions, so `mcp_protocol.py` implements the necessary
  subset (JSON-RPC 2.0, `initialize`/`tools/list`/`tools/call`, stdio
  transport) directly against the standard library.
- **Role-scoped agents via explicit tool registries, not prompt-only
  restriction**: the Committee Agent cannot call `log_service_request`
  because that function is never in its `tool_registry` — not because the
  system prompt asks it not to.
- **Bounded, synchronous workflow execution**: no job queue, no
  persistence, a fixed step cap. For this project's realistic workflow
  sizes, that's a deliberate simplicity tradeoff, not an oversight.
- **PostgreSQL**: relational data with real foreign keys (flat → building,
  resident → flat, service request → flat/resident/vendor) suits this
  domain better than a document store; Alembic gives reproducible schema
  history.
- **Local-first via Ollama**: the default configuration has zero external
  API cost and works offline, while `ClaudeProvider` exists as a drop-in
  swap (one config value) for anyone who wants a hosted model instead.

## Security / Production Considerations

**Implemented today:**

- Input validation via Pydantic schemas on every REST endpoint
- CORS restricted to configured origins
- Resident-tool write access scoped to the caller-supplied resident (not
  LLM-suppliable), as described above

**Not yet implemented — required before any real production deployment:**

- **Authentication/authorization** — there is currently no login system or
  RBAC; every REST endpoint and the AI Assistant's `role` field are
  unauthenticated. Anyone who can reach the API can call any endpoint or
  select the committee agent.
- **Rate limiting** — no request throttling on any endpoint, including the
  LLM-backed ones.
- **Secrets management** — credentials are read from a local `.env` file;
  no vault/secret-manager integration.
- **Audit logging** — actions like vendor assignment or workflow execution
  are not logged for after-the-fact review.
- **Background job infrastructure** — `WorkflowAgent` runs synchronously
  within the request; there is no queue, worker, or job-status tracking.
- **Workflow history/persistence** — each workflow run is stateless; no run
  is saved or retrievable afterward.
- **HTTPS/production deployment configuration** — not addressed by this
  repository (development-only `uvicorn --reload` / `vite dev` setup).

## Future Roadmap

- Authentication and role-based access control for the REST API and AI Assistant
- Persisted workflow run history
- Background execution for longer-running workflows
- Additional LLM providers behind the existing `LLMProvider` interface
- Expanded MCP tool coverage (e.g. vendor assignment tools already exist in
  `WorkflowAgent`'s tool set and could be exposed via MCP as well)

## Author

*Repository author information not present in the current project — add here.*