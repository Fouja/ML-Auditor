# ML-Auditor Architecture

## System Overview

ML-Auditor is a modular monolithic application with three main services:

```
┌──────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                    │
│              (SSL termination, rate limiting)             │
├──────────────┬──────────────┬────────────────────────────┤
│  Frontend    │   Backend    │      ML Service            │
│  Next.js 14  │  Django 4.2  │    FastAPI + CrewAI        │
│  Port 3000   │  Port 8000   │      Port 8001             │
└──────┬───────┴──────┬───────┴─────────┬──────────────────┘
       │              │                 │
       │         ┌────┴────┐           │
       │         │ Postgres│           │
       │         │  16 +   │           │
       │         │ pgvector│           │
       │         └────┬────┘           │
       │              │                │
       │         ┌────┴────┐           │
       │         │  Redis  │           │
       │         │ Cache + │           │
       │         │ Celery  │           │
       │         └─────────┘           │
       │                               │
       └─────── NVIDIA NIM API ────────┘
```

## Backend Architecture

### Django Apps

| App | Responsibility | Models |
|-----|---------------|--------|
| `users` | Authentication, JWT, OAuth clients | User (UUID PK, IMAP/Canva fields) |
| `workspace` | Tasks, Calendar, News, Widgets | Task, CalendarEvent, NewsFeed, NewsArticle, WorkspaceWidget, Trigger |
| `agents` | AI orchestration, tools, workflows | (service layer, no models) |
| `integrations` | Email/Calendar/Plaid/Canva/Kijiji | IntegrationConnection, SyncLog |
| `alerts` | Alert system | Alert |
| `data_streams` | Data pipeline | DataStream |
| `document_chunks` | RAG embeddings | DocumentChunk (pgvector) |

### API Layer (Django Ninja)

- 29 integration endpoints
- 8 agent endpoints
- 6+ workspace endpoints per resource
- JWT authentication via `JWTAuthenticationMiddleware`
- Rate limiting via DRF throttling (100/hr anon, 1000/hr user)

### Async Tasks (Celery)

- **Queues**: default, email, calendar, plaid, kijiji, canva
- **Beat schedule**: Gmail hourly, Plaid every 4h
- **Workers**: 4 concurrent (configurable)

### WebSocket Channels

- `alerts/` - Real-time alerts
- `analytics/` - Live analytics updates
- `notifications/` - Push notifications

## Frontend Architecture

### Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Landing page | Marketing / redirect |
| `/login` | Login form | Email + password auth |
| `/register` | Register form | New user signup |
| `/dashboard` | Tab switcher | Wall of Work (default) / Bento grid |
| `/dashboard/integrations` | Integration panel | IMAP, Gmail, Plaid, Canva, Kijiji |
| `/dashboard/notifications` | Notification prefs | Toggle switches, severity rules |
| `/settings` | User settings | Profile, theme |

### State Management

- **Zustand**: Auth store, UI state
- **TanStack Query**: Server state, caching, refetching

### Key Components

- `wall-of-work.tsx` - Kanban board with drag-and-drop, inline priority editing, overdue detection
- `bento-grid.tsx` - Dashboard widgets grid
- `chatbot-panel.tsx` - AI chatbot with 2-step confirmation
- `integrations-panel.tsx` - Multi-provider integration setup
- `omni-chat.tsx` - Unified chat interface

## ML Service Architecture

### Services

| Service | Function |
|---------|----------|
| `classifier.py` | Email classification via NIM |
| `entity_extractor.py` | Named entity recognition |
| `anomaly_detector.py` | Isolation Forest anomaly detection |
| `embeddings.py` | pgvector embedding generation |
| `search.py` | RAG document search |
| `kijiji_classifier.py` | Kijiji listing analysis |
| `financial_analyzer.py` | Transaction insights |
| `ml_client.py` | Django → ML HTTP client |

### NVIDIA NIM Integration

- **Model**: Llama 3.3 70B (classification, chat)
- **Embeddings**: nvidia/nv-embedqa-e5-v5
- **Lazy initialization**: Service starts without API key

## Data Flow

```
User Action → Frontend → Django API → Celery Task → External API
                                              ↓
                                    ML Service (NIM)
                                              ↓
                                    PostgreSQL (pgvector)
                                              ↓
                                    WebSocket → Frontend
```

## Security

- JWT tokens with 1h access / 7d refresh
- Token blacklisting on logout
- OAuth token encryption at rest
- CSRF protection + HttpOnly cookies
- Rate limiting per IP
- Input sanitization (XSS prevention)
- Security headers (HSTS, CSP, X-Frame-Options)

## Scalability

- Horizontal: Multiple Celery workers, backend replicas
- Vertical: Gunicorn workers, ML service workers
- Database: Read replicas, connection pooling
- Cache: Redis with LRU eviction
- CDN: Static files via Nginx/CloudFlare
