# ML-Auditor Architecture

Full system architecture: services, data flow, logging pipeline, and how everything connects.

---

## 1. High-Level Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              Users (Browser)                             │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                    HTTP/WS │ NEXT_PUBLIC_API_URL=http://localhost:8000
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         Nginx Reverse Proxy                              │
│             (prod only: SSL termination, static files, routing)          │
└──────┬────────────────────────────┬──────────────────────────────────────┘
       │ :3000                      │ :8000
       ▼                            ▼
┌──────────────┐          ┌──────────────────┐
│  Frontend    │◄────────►│  Backend          │
│  Next.js 16  │  REST    │  Django 4.2      │
│  React 19    │  JSON    │  Django Ninja    │
│  Tailwind    │          │  LangGraph       │
│  TanStack Q. │          │  Celery Workers  │
│  Zustand     │          │  Channels (WS)   │
└──────────────┘          │  MCP Server      │
                          └──────┬──────┬────┘
                                 │      │
                     ┌───────────┴┐  ┌──┴────────┐  ┌────────┴────────┐
                     │ PostgreSQL │  │  Redis 7  │  │  NVIDIA NIM     │
                     │     16     │  │  Cache +  │  │  API (cloud)    │
                     │  pgvector  │  │  Celery   │  │  build.nvidia   │
                     │  vector(1024)│  │  Broker   │  └─────────────────┘
                     └────────────┘  └───────────┘
```

> **Call paths (current reality):** The Backend calls **NVIDIA NIM directly**
> over HTTPS. It orchestrates the assistant loop with **LangGraph**
> (`agent_graph.py`) using `langchain-openai`'s `ChatOpenAI` for chat
> completions + tool calling, and calls the NIM embeddings endpoint from
> `embedding_generation.py`. The **ML Service (FastAPI) was removed** — all
> AI features are served by the backend itself, which also exposes its tools
> over an **MCP server** (`apps/agents/mcp_server.py`, stdio or :8100).
> Additionally the backend acts as an **MCP client** (`mcp_client.py`) to
> consume the web-tools (Agent-Reach) and JobChameleon MCP endpoints.

### Service Responsibilities

| Service | Tech | Port | Responsibility |
|---------|------|------|----------------|
| **Frontend** | Next.js 16, React 19, Tailwind CSS | 3000 | UI rendering, user interactions, dashboard |
| **Backend** | Django 4.2, Django Ninja, LangGraph, Celery, Channels | 8000 | REST API, auth, business logic, AI agent orchestration (chat, embeddings, email/bank classification), integrations, background jobs, WebSocket, MCP server |
| **Database** | PostgreSQL 16 | 5432 | Primary data store (pgvector `vector(1024)` in `DocumentChunk`) |
| **Cache** | Redis 7 | 6379 | Session cache, Celery broker, WebSocket channels |

---

## 2. Frontend → Backend Communication

### REST API (JSON over HTTP)

All frontend communication goes through the Django backend REST API.

```
Frontend  ───── POST /api/users/login ──────►  Backend
         ◄───── { access_token, ... } ───────

Frontend  ───── GET /api/integrations/status ──►  Backend
         ◄───── { email, calendar, ... } ───────

Frontend  ───── POST /api/agents/chat ───────►  Backend
         ◄───── { response, actions_taken } ───
```

**Axios instance** (`frontend/src/lib/api.ts`):
- `baseURL` = `NEXT_PUBLIC_API_URL` + `/api`
- Automatically attaches `Authorization: Bearer <token>` from localStorage via request interceptor
- Automatically refreshes expired tokens on 401 responses via response interceptor
- Logs every request/response via `FrontendLogger`

### WebSocket (Channels)

For real-time features (notifications, live task updates):

```
Frontend  ───── WS /ws/notifications/ ──────►  Backend (Channels)
         ◄───── { type: "task_updated", ... } ─

Frontend  ───── WS /ws/alerts/ ─────────────►  Backend (Channels)
         ◄───── { type: "alert_created", ... }

Frontend  ───── WS /ws/analytics/ ──────────►  Backend (Channels)
```

WebSocket routes are defined in `apps/agents/routing.py` (imported by `config/asgi.py`):
`ws/alerts/` → `AlertsConsumer`, `ws/analytics/` → `AnalyticsConsumer`,
`ws/notifications/` → `NotificationsConsumer` — all three consumers live in
`apps/alerts/consumers.py`.

### API URL Resolution

```
.env variable:        NEXT_PUBLIC_API_URL=http://localhost:8000
Axios baseURL:        http://localhost:8000/api
Example full URL:     http://localhost:8000/api/workspace/notes
```

---

## 3. Backend Internal Architecture

### Django Apps

```
backend/
├── config/               # Django settings, root URL config, Celery, ASGI
│   ├── settings.py       # All env vars + structured JSON logging
│   ├── urls.py           # /admin/, /api/ → Ninja api.urls, /api/logs/
│   ├── api.py            # NinjaAPI instance + app router registration
│   ├── celery.py         # Celery application
│   └── wsgi.py / asgi.py # Entry points (ASGI: HTTP + WebSocket)
│
├── apps/
│   ├── users/            # Auth (JWT), OAuth, user model, middleware
│   │   ├── api.py        # login, register, refresh, me
│   │   ├── models.py     # User (email-based, UUID pk)
│   │   ├── auth.py       # JWTAuth (HttpBearer) used by Ninja
│   │   ├── middleware.py # RequestLoggingMiddleware, ErrorHandling, JWTAuth
│   │   └── services/     # External clients + OAuth helpers:
│   │       ├── email_client.py    # IMAP/SMTP client
│   │       ├── gmail_client.py    # Gmail API (OAuth)
│   │       ├── calendar_client.py # Google Calendar
│   │       ├── plaid_client.py    # Banking transactions
│   │       ├── canva_client.py    # Canva designs
│   │       ├── jira_client.py     # Jira REST v3 + RAG search
│   │       ├── kijiji_scraper.py  # Kijiji marketplace scraper
│   │       ├── base_oauth.py      # Shared OAuth flow
│   │       ├── token_encryption.py
│   │       └── input_validation.py
│   │
│   ├── workspace/        # Tasks, Calendar, News Feeds, Widgets, Notes
│   │   ├── api.py        # Task/Event/Feed/Article/Widget/Note CRUD + note generate
│   │   ├── models.py     # Task, Event, Feed, Article, Widget, Note
│   │   ├── tasks.py      # Celery: scrape_news_feeds, check_triggers
│   │   └── schemas.py    # Pydantic request/response schemas
│   │
│   ├── agents/           # AI agent orchestration (the "brain") — no models
│   │   ├── api.py        # Chat, agent status, workflows, voice, notifications
│   │   ├── schemas.py    # AgentMessage, AgentResponse, AgentStatus
│   │   ├── mcp_server.py # MCP server: exposes agent tools (stdio / StreamableHTTP :8100)
│   │   └── services/
│   │       ├── agent_command.py      # Entry point: process_message, personas, tool schema
│   │       ├── agent_graph.py        # LangGraph state machine: RAG → LLM → tools loop
│   │       ├── bank_statement_pdf.py # Formal PDF bank statement generator (reportlab)
│   │       ├── tool_executor.py      # Tool registry → runs backend actions
│   │       ├── workflows.py          # Multi-step smart workflows
│   │       ├── notifications.py      # Alert severity rules + routing
│   │       ├── agent_execution.py    # Celery: execute_agent_job, classify_email, detect_anomalies
│   │       ├── kijiji_scraper_job.py # Celery: Kijiji jobs + stream cleanup
│   │       └── mcp_client.py         # MCP client → web-tools / JobChameleon MCP servers
│   │
│   ├── integrations/     # External connectors + LLM configuration
│   │   ├── api.py        # Integration status + actions + cluster endpoints
│   │   ├── llm_api.py    # LLM Configuration CRUD + test + set-active
│   │   ├── llm_config.py / llm_models.py
│   │   ├── models.py     # LLMConfiguration, IntegrationConnection, SyncLog
│   │   ├── tasks.py      # Celery: sync_email/gmail/calendar/plaid/canva/jira/kijiji
│   │   └── schemas.py
│   │
│   ├── document_chunks/  # RAG document storage + embeddings
│   │   ├── api.py / schemas.py
│   │   ├── models.py     # DocumentChunk (pgvector vector(1024) + cluster_category)
│   │   └── services/
│   │       ├── embedding_generation.py  # NIM embedding API + RAG helpers
│   │       └── email_clustering.py      # Email classification → DocumentChunks
│   │
│   ├── alerts/           # Rule-based alerts + WebSocket consumers + WS routing
│   │   ├── api.py / models.py / schemas.py
│   │   ├── consumers.py  # AlertsConsumer, AnalyticsConsumer, NotificationsConsumer
│   │   ├── routing.py    # ws/alerts, ws/analytics, ws/notifications
│   │   └── services/
│   │
│   ├── data_streams/     # Data ingestion pipelines
│   │   ├── api.py / models.py / schemas.py
│   │   └── services/
│   │       └── email_analysis.py  # Celery: analyze_email_job
│   │
│   └── logs/             # Log receiver
│       └── urls.py / views.py    # POST /api/logs/
│
└── tests/                # pytest: test_api.py, test_models.py, test_services.py, test_agent_graph.py, test_bank_statement.py
```

### Request Lifecycle

```
1. HTTP Request arrives at Django
2. └── JWTAuthenticationMiddleware → validates Bearer token → sets request.auth
3. └── RequestLoggingMiddleware → logs: method, path, status, timing, user_id
4. └── Django Ninja Router → matches URL pattern → calls view function
5. └── View function → processes request → returns JSON response
6. └── ErrorHandlingMiddleware → catches exceptions → returns structured error
7. └── Log entry written to logs/backend/django.log + console
```

---

## 4. AI & MCP Surface

**There is no separate ML Service anymore.** The Django backend is the single
owner of all AI work and calls **NVIDIA NIM directly** over HTTPS for every AI
feature.

Chat/tool orchestration runs through **LangGraph** (`agent_graph.py`), which
builds a `ChatOpenAI` client (`langchain-openai`) pointed at the NIM endpoint
and executes tool calls through `ToolExecutor`:

```
Backend (agent_graph.py :: call_model node) ── ChatOpenAI.ainvoke(tools) ──► NVIDIA NIM API
                                          ◄── AIMessage (text and/or tool_calls) ─

Backend (execute_tools node) ── ToolExecutor.execute(name, args) ──► backend services
                              ◄── { success, ... } (fed back as ToolMessage) ─

Backend (embedding_generation.py) ── POST {NIM_BASE_URL}/embeddings ──► NVIDIA NIM API
                                 ◄── { data: [{"embedding": [...] }] } ──
```

### MCP Server (tools for any LLM)

`apps/agents/mcp_server.py` exposes the agent's tools (tasks, notes, calendar,
live web search/fetch, news, Agent-Reach status, JobChameleon scoring) over the
Model Context Protocol. Any MCP client (Claude, Cursor, opencode, mcporter…)
can connect:

- stdio: `python -m apps.agents.mcp_server`
- StreamableHTTP: `python -m apps.agents.mcp_server --http --port 8100`

The backend is also an **MCP client** (`apps/agents/services/mcp_client.py`),
consuming the web-tools (Agent-Reach) and JobChameleon MCP endpoints, and
exposes a passthrough REST endpoint (`POST /api/agents/jobchameleon/mcp`).

---

## 5. Logging & ELK Stack

### Log Generation

Every service writes structured JSON logs to the shared `logs/` directory:

```
logs/
├── backend/
│   └── django.log          # Django JSONFormatter → one JSON object per line
└── frontend/
    └── frontend.log        # FrontendLogger → POST /api/logs/ → backend writes
```

### Log Format (all services)

```json
{
  "@timestamp": "2026-07-28 01:08:56,381",
  "level": "INFO",
  "service": "backend",
  "stack": "django",
  "message": "\"POST /api/users/login HTTP/1.1\" 200 609",
  "logger": "django.server",
  "module": "server",
  "function": "log_message",
  "line": 42
}
```

### ELK Pipeline (inside Docker)

```
┌──────────┐    ┌───────────┐    ┌───────────────┐    ┌────────────┐
│ Backend  │    │ Filebeat  │    │  Logstash     │    │Elasticsearch│
│ logs/    │───►│ reads .log├───►│  pipeline:    ├───►│  index:     │
│ django.log│   │ files     │    │  filter +     │    │  ml-auditor-│
├──────────┤   └───────────┘    │  enrich +     │    │  backend-*  │
│Frontend  │                    │  tag          │    ├────────────┤
│ logs/    │────────────────────►               │    │  ml-auditor-│
│frontend+ │   TCP :5000         │               │    │  frontend-* │
│django.log│                    │               │    ├────────────┤
└──────────┘                    └───────────────┘    │  ml-auditor-│
                                                      │  tcp-ingest │
                                                      └──────┬─────┘
                                                             │
                                                      ┌──────▼─────┐
                                                      │   Kibana   │
                                                      └─── port 5601
```

**Two ingestion paths:**

1. **Filebeat** (default) — Filebeat watches `logs/*.log` files and ships to Logstash via the Beats protocol on port 5044. This is the primary path for all services.

2. **TCP** (for demos/external) — Logstash listens on port 5000. You can send JSON from any source:
   ```bash
   echo '{"message":"hello from my script","service":"demo"}' | nc localhost 5000
   ```

### Logstash Processing

Each log entry goes through the `docker/logstash/pipeline/logstash.conf` pipeline:

1. **Input** — reads from file paths or TCP
2. **Filter** — adds `service` and `stack` fields, parses timestamps, classifies `event_type` (info/warning/error/http_request), applies tags (auth, crud, ai)
3. **Output** — writes to Elasticsearch index `ml-auditor-{type}-{YYYY.MM.dd}`

### Kibana Dashboards

Pre-built saved objects in `docker/kibana/saved-objects.ndjson`:

| Name | Type | Query |
|------|------|-------|
| `ml-auditor-backend` | Index pattern | `ml-auditor-backend-*` |
| `ml-auditor-frontend` | Index pattern | `ml-auditor-frontend-*` |
| `ml-auditor-tcp-ingest` | Index pattern | `ml-auditor-tcp-ingest-*` |
| All Logs | Saved search | (no filter) |
| All Errors | Saved search | `level: ERROR or level: CRITICAL` |
| HTTP Requests | Saved search | `event_type: http_request` |
| Auth Events | Saved search | `tags: auth` |
| AI Agent Logs | Saved search | `tags: ai` |
| External Ingest | Saved search | (all tcp-ingest) |

**To import:** Kibana → Stack Management → Saved Objects → Import → select `docker/kibana/saved-objects.ndjson`

### Elasticsearch Indices

```
ml-auditor-backend-2026.07.28      # Django backend logs
ml-auditor-frontend-2026.07.28     # Frontend logs
ml-auditor-tcp-ingest-2026.07.28   # TCP ingest logs
```

### Useful Kibana Queries (KQL)

```kql
service: backend
level: ERROR
service: frontend AND level: warn
status_code >= 400
tags: auth AND level: ERROR
event_type: http_request AND service: backend
message: login
```

### Connecting New Services to ELK

Any service can send logs to ELK three ways:

1. **Write JSON to a file** mounted under `logs/<service>/` — Filebeat picks it up automatically
2. **Send JSON via TCP** to `localhost:5000` — Logstash ingests it directly
3. **POST to backend** `POST /api/logs/` — Django writes to `django.log`, then Filebeat picks it up

---

## 6. RAG Pipeline

```
User asks a question
         │
         ▼
agent_command.py::process_message()
         │  ── delegates to ──►  agent_graph.py::run_agent()
         │
         ▼
     LangGraph: retrieve_context node
         │
         ├──► _retrieve_rag_context()
         │       │
         │       ├──► Query DocumentChunks table (pgvector OR keyword)
         │       │       │
         │       │       ├── If real embeddings exist: pgvector <=> cosine distance
         │       │       │       in SQL (HNSW index, scored > 0.3 kept, top 5)
         │       │       └── If not (zero-vectors / no API key): keyword match
         │       │               (content__icontains per word, top 5)
         │       │
         │       └──► Returns: "[<source>] <chunk content>" blocks appended to prompt
         │
         ▼
     LangGraph: call_model node
         │
         ├──► _get_nim_config()
         │       │
         │       ├──► Check NIM_API_KEY env var first
         │       └──► Fallback: user's active LLMConfiguration from DB (is_active=True)
         │
         ├──► ChatOpenAI(model, base_url, temperature=0.3).bind_tools(AVAILABLE_TOOLS).ainvoke()
         │       │
         │       └──► If no API key: canned "AI services are not configured" (stops)
         │
         ▼
     LangGraph: should_continue ──► END (final text response)
         │   │
         │   └── tool_calls present & iterations < 5 ──► execute_tools node
         │           │
         │           ├──► ToolExecutor.execute(name, args) → backend services
         │           └──► ToolMessage(result JSON) fed back → back to call_model node
```

### Document Sources for RAG

| Source | How it gets into DocumentChunks |
|--------|--------------------------------|
| Jira issues | Celery task `sync_jira_for_user` → Jira API → `DocumentChunk.create()` (+ embedding) |
| Email (IMAP) | Celery `sync_email` → `index_email_messages` (heuristic + LLM classification) → chunks |
| Gmail (OAuth2) | Celery `sync_gmail_for_user` → Gmail API → `index_email_messages` → chunks |
| Bank transactions (Plaid) | Celery `sync_plaid_for_user` → `index_plaid_transactions` → chunks |
| Custom | Via API or data streams |

### Embedding Model

- **Model**: `nvidia/nv-embedqa-e5-v5` via NVIDIA NIM API
- **Storage**: `DocumentChunk.embedding` is a real **pgvector `vector(1024)`** column (migration `0004_vector_embedding`), backed by an **HNSW cosine index** (`document_chunks_embedding_idx`, `USING hnsw (embedding vector_cosine_ops)`)
- **Search**: `apps/document_chunks/services/rag/retriever.py` runs real SQL `<=>` cosine distance via `pgvector.django.CosineDistance`; falls back to keyword matching when the query embedding is unavailable
- **Dimension**: **1024** (`DIMENSIONS = 1024` in `embedding_generation.py`)
- **Fallback**: Zero-vector when no NIM API key → RAG falls back to keyword matching

---

## 7. Frontend Component Tree

```
DashboardPage (app/dashboard/page.tsx)
├── DashboardLayout
│   └── Toaster (bottom-right toast notifications)
├── Tab bar: [Wall of Work] [Dashboard] [Notes] [News] [Clusters]
├── Content area
│   ├── WallOfWork (board tab)
│   ├── Notes (notes tab)
│   │   ├── Note list (left panel) + Note editor (right panel)
│   │   ├── Tag input, format selector, pin, delete
│   │   └── Generate buttons (presentation, chapter, article)
│   ├── ClusterBoard (clusters tab — email + bank transaction clusters)
│   └── BentoGrid (dashboard tab)
│       ├── CalendarWidget
│       ├── NewsFeedWidget
│       └── OmniChat
└── Right sidebar (w-96)
    └── ChatbotPanel
        ├── Message list (renders PDF download link when metadata.file_url present)
        ├── Input + send
        ├── API Key dialog (Add API Key button)
        └── IntegrationsPanel (toggle)
            ├── EmailSection
            ├── GmailSection
            ├── CalendarSection
            ├── PlaidSection
            ├── CanvaSection
            ├── KijijiSection
            └── JiraSection
```

### State Management

| Type | Tool | What it manages |
|------|------|-----------------|
| Server state | TanStack Query (React Query) | API data: integrations status, Jira projects, notes list |
| UI state | React useState | Form inputs, dialog visibility, selected items |
| Auth state | useAuth hook | JWT tokens, user info |
| Chat state | useReducer | Message history, loading state |

---

## 8. Data Flow Examples

### A. User logs in

```
1. Frontend: POST /api/users/login { email, password }
2. Backend:  validate credentials → generate JWT access + refresh tokens
3. Frontend: store tokens in localStorage
4. Frontend: fetch user profile via GET /api/users/me
5. Frontend: fetch dashboard data (tasks, widgets, integrations status)
6. Frontend: connect WebSocket for real-time updates
```

### B. User asks chatbot a question

```
1. Frontend: POST /api/agents/chat { content: "show my jira issues", agent_type: "general" }
2. Backend:  agent_command.py::process_message() → agent_graph.py::run_agent()
3. Backend:  LangGraph retrieve_context node → _retrieve_rag_context() → searches DocumentChunks
4. Backend:  LangGraph call_model node → _get_nim_config() → ChatOpenAI (NIM) with tools
5. Backend:  NIM responds with an AIMessage (text and/or tool_calls)
6. Backend:  LangGraph execute_tools node → tool_executor.py runs jira_get_issues() → Jira REST API
7. Backend:  ToolMessage fed back → call_model node → final text response
8. Backend:  Returns structured response + actions_taken array (+ metadata.file_url if a file was generated)
9. Frontend: Renders response text + action buttons / PDF download link if any
```

### B2. User asks for a bank statement PDF

```
1. Frontend: POST /api/agents/chat { content: "get my bank statement for May 2026", agent_type: "general" }
2. Backend:  LangGraph call_model node → model decides to call get_bank_statement_pdf { month: 5, year: 2026 }
3. Backend:  execute_tools node → tool_executor._exec_get_bank_statement_pdf
4. Backend:  bank_statement_pdf.generate_bank_statement_pdf(user, 5, 2026)
5. Backend:  PlaidClient → accounts + transactions (paginated) for the month
6. Backend:  reportlab builds a formal letterhead PDF (bank logo/name/address, holder info,
             summary, itemised transactions) → media/bank_statements/<user_id>/bank-statement-YYYY-MM.pdf
7. Backend:  ToolMessage result (incl. file_url) fed back → model confirms in text
8. Backend:  metadata.file_url included in the API response
9. Frontend: ChatbotPanel renders a "Download bank statement (PDF)" link
10. Dev:     Django serves /media/ via config/urls.py (DEBUG only); prod: nginx serves /media/ → /app/media/
```

### C. User configures Jira integration

```
1. Frontend: POST /api/integrations/jira/configure { site_url, email, api_token }
2. Backend:  saves to DB, calls Jira API to verify connection
3. Frontend: fetches Jira projects via GET /api/integrations/jira/projects
4. User:     selects a project
5. Frontend: fetches issues via POST /api/integrations/jira/issues { project_key }
6. User:     clicks "Sync to RAG"
7. Frontend: POST /api/integrations/jira/sync
8. Backend:  Celery task sync_jira_for_user() → fetches issues → creates DocumentChunks
9. Frontend: shows success toast "Synced N issues to RAG"
```

### D. Logs flow through ELK

```
1. User:     sends a chat message
2. Backend:  RequestLoggingMiddleware logs: { method:"POST", path:"/api/agents/chat", ... }
3. Backend:  JSONFormatter writes to logs/backend/django.log
4. Filebeat: reads new line from django.log → sends to Logstash :5044
5. Logstash: parses JSON, adds tags (service:backend, event_type:http_request)
6. Logstash: outputs to Elasticsearch index ml-auditor-backend-2026.07.28
7. Kibana:   user searches "service:backend AND status_code:200" via Discover
```

---

## 9. Port Reference

| Port | Service | Protocol | Purpose |
|------|---------|----------|---------|
| 3000 | Frontend | HTTP | Next.js dev server / production |
| 5432 | PostgreSQL | TCP | Database |
| 6379 | Redis | TCP | Cache + Celery + Channels |
| 8000 | Backend | HTTP | Django REST API + MCP server (8100) |
| 9200 | Elasticsearch | HTTP | Log storage + search API |
| 5601 | Kibana | HTTP | Log visualization dashboard |
| 5000 | Logstash | TCP | Live log ingestion (for demos) |
| 5044 | Logstash | Beats | Filebeat log shipping |
| 9600 | Logstash | HTTP | Monitoring API |
| 9090 | Prometheus | HTTP | Metrics (prod only) |
| 3001 | Grafana | HTTP | Dashboards (prod only) |

---

## 10. Environment Variables Reference

| Variable | Where used | Default | Required? |
|----------|-----------|---------|-----------|
| `NEXT_PUBLIC_API_URL` | Frontend | `http://localhost:8000` | Yes |
| `NEXT_PUBLIC_WS_URL` | Frontend | `ws://localhost:8000` | Yes |
| `DJANGO_DEBUG` | Backend | `False` | Yes |
| `DJANGO_SECRET_KEY` | Backend | — | Yes (prod) |
| `JWT_SECRET_KEY` | Backend | — | Yes (prod) |
| `DJANGO_DATABASE_URL` | Backend | `postgres://...` | Yes |
| `NIM_API_KEY` | Backend | `""` | For AI features |
| `NIM_BASE_URL` | Backend | `https://integrate.api.nvidia.com/v1` | No |
| `NIM_MODEL` | Backend | `meta/llama-3.3-70b-instruct` | No |
| `NIM_EMBEDDING_MODEL` | Backend | `nvidia/nv-embedqa-e5-v5` | No |
| `BANK_STATEMENT_BRANDING` | Backend | defaults | JSON dict for PDF letterhead: bank_name, logo_path, address_lines, phone, website, email |
| `ELASTICSEARCH_URL` | Backend, Compose | `http://localhost:9200` | For ELK |

---

## 11. Docker Compose Services

### `docker-compose.yml` (development)

```yaml
services:
  db              # PostgreSQL 16 + pgvector
  redis           # Redis 7
  backend         # Django 4.2 (dev mode: hot reload)
  celery_worker   # Celery worker
  celery_beat     # Celery beat scheduler
  frontend        # Next.js (dev mode: hot reload)
  elasticsearch   # Elasticsearch 8.13 (single node, no auth)
  logstash        # Logstash 8.13 with pipeline
  kibana          # Kibana 8.13
  filebeat        # Filebeat 8.13 (ships logs from volumes)
```

### `docker-compose.prod.yml` (production)

Same services plus:
- `nginx` — reverse proxy with SSL
- `prometheus` — metrics collection
- `grafana` — metrics dashboards
- `loki` — alternative log aggregation (Grafana stack)

### Shared Volumes

```yaml
volumes:
  postgres_data:      # Database persistence
  redis_data:         # Redis persistence
  static_files:       # Django collected static files
  media_files:        # User-uploaded media
  elasticsearch_data: # Log index data
  logstash_data:      # Logstash state (sincedb)
  filebeat_data:      # Filebeat registry
```

## 10. Secrets Management

Credentials are never stored in plaintext:

- **At rest:** `LLMConfiguration.api_key` is encrypted with Fernet (AES-128-CBC
  + HMAC-SHA256) before being written. The key is derived from
  `SECRET_ENCRYPTION_KEY` (falling back to `DJANGO_SECRET_KEY`) by
  `config/security.py`. Encrypted values carry an `enc::` prefix; legacy
  plaintext rows are upgraded by `migrations/0004_*`.
- **In transit:** NIM, JobChameleon, Web Tools, and EXA credentials come from
  environment variables injected at runtime (never baked into images or
  committed).
- **Defaults:** `docker-compose.yml` has no fallback secrets, and
  `config/settings.py` refuses to boot in non-debug mode with placeholder
  `DJANGO_SECRET_KEY`/`JWT_SECRET_KEY` values.
- **Generation:** `scripts/generate_secrets.sh` fills missing secrets
  idempotently.

See `docs/SECURITY.md` for the full posture and rotation guidance.

Log files are shared via bind mount `./logs:/var/log/ml-auditor:ro` so Filebeat and Logstash can access them.
