# PLAN DE DÉVELOPPEMENT DÉTAILLÉ - JARVIS OMNISCIENT (2026)

**Statut** : EN COURS DE DÉVELOPPEMENT  
**Date de création** : 2026-07-19  
**Durée estimée totale** : ~480-520 heures (12-13 semaines à temps plein)

---

## 📊 RÉSUMÉ EXÉCUTIF

### Phases de Développement
- **PHASE 0** : Initialisation & Infrastructure (40-50h)
- **PHASE 1** : Backend Rails 8 (120-140h)
- **PHASE 2** : Frontend React 19 (100-120h)
- **PHASE 3** : ML Python & Clustering (80-100h)
- **PHASE 4** : Intégrations Externes (60-80h)
- **PHASE 5** : Features Agents & Workflows (50-60h)
- **PHASE 6** : Tests & Optimisation (30-40h)
- **PHASE 7** : Déploiement & Documentation (20-30h)

### Tâches Transversales
- Sécurité & Chiffrement (15-20h)
- Monitoring & Logging (15-20h)

**Total estimé : 430 tâches réparties sur 8 phases**

---

## 🏗️ PHASE 0 : INITIALISATION & INFRASTRUCTURE

### 0.1 - Setup Monorepo & Repositories

- [ ] **TASK-001** [P5] Créer la structure monorepo avec yarn workspaces
  - **Description** : Initialiser un monorepo avec structure `/apps` (backend, frontend) et `/packages` (shared utils)
  - **Dépendances** : Aucune
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Node.js, Yarn 4+
  - **Critères d'acceptation** :
    - Structure monorepo fonctionnelle
    - Configuration yarn workspaces correcte
    - Scripts de build cross-monorepo
    - README avec instructions d'installation

- [ ] **TASK-002** [P5] Initialiser le repository Git avec CI/CD (GitHub Actions)
  - **Description** : Configurer .gitignore, .github/workflows pour build/test automatisés
  - **Dépendances** : TASK-001
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Git, GitHub Actions
  - **Critères d'acceptation** :
    - Workflows lint, build, test activés
    - .gitignore complet pour Rails + React + Python
    - Branch protection rules configurées

- [ ] **TASK-003** [P5] Configurer Docker & Docker Compose pour dev local
  - **Description** : Créer Dockerfile pour Rails, React, PostgreSQL, Python microservice
  - **Dépendances** : TASK-001
  - **Temps estimé** : 4h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Docker, Docker Compose
  - **Critères d'acceptation** :
    - docker-compose.yml avec tous les services
    - Services communiquent correctement
    - Volumes configurés pour hot-reload
    - Scripts de setup (`make dev-up`, `make dev-down`)

- [ ] **TASK-004** [P5] Configurer PostgreSQL 16 avec extension pgvector
  - **Description** : Initialiser la base de données avec support HNSW, créer scripts de migration
  - **Dépendances** : TASK-003
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : PostgreSQL 16, pgvector, Docker
  - **Critères d'acceptation** :
    - pgvector installé et activé
    - Extension vector accessible via psql
    - Migrations Rails générées
    - Scripts seed pour données de test

### 0.2 - Configuration Environnement

- [ ] **TASK-005** [P5] Configurer variables d'environnement (.env, .env.local)
  - **Description** : Créer templates .env.example pour tous les services
  - **Dépendances** : TASK-001
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Bash, dotenv
  - **Critères d'acceptation** :
    - .env.example documenté
    - Toutes clés API listées (NVIDIA_NIM, Google OAuth, etc.)
    - Instructions de configuration dans README

- [ ] **TASK-006** [P5] Configurer secrets management (Rails credentials, .env)
  - **Description** : Implémenter Rails credentials pour prod, local .env pour dev
  - **Dépendances** : TASK-005
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails 8, dotenv, OpenSSL
  - **Critères d'acceptation** :
    - rails credentials:edit fonctionnel
    - Fallback sur ENV vars
    - Documentation sur rotation des clés

### 0.3 - Tooling & Development Setup

- [ ] **TASK-007** [P4] Configurer ESLint + Prettier pour React/Next.js
  - **Description** : Setup ESLint config (eslint-config-next), Prettier formatting
  - **Dépendances** : TASK-001
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : ESLint, Prettier, Node.js
  - **Critères d'acceptation** :
    - Linting passe sans erreurs
    - Format on save configuré
    - Intégration CI/CD pour lint

- [ ] **TASK-008** [P4] Configurer Rubocop + Prettier pour Rails
  - **Description** : Setup Rubocop config pour Rails, integration avec IDE
  - **Dépendances** : TASK-001
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Rubocop, Ruby 3.4
  - **Critères d'acceptation** :
    - Rubocop config personnalisé
    - Format on save dans VS Code
    - CI check pour violations

- [ ] **TASK-009** [P4] Configurer Pytest + Black pour Python ML
  - **Description** : Setup Pytest, Black formatter, isort pour microservice Python
  - **Dépendances** : TASK-001
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Python 3.13, Pytest, Black
  - **Critères d'acceptation** :
    - Pytest discovery configuré
    - Black check dans CI
    - Isort pour import sorting

- [ ] **TASK-010** [P4] Configurer Husky + Pre-commit hooks
  - **Description** : Setup pre-commit hooks pour lint, format, tests rapides
  - **Dépendances** : TASK-007, TASK-008
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Husky, Node.js
  - **Critères d'acceptation** :
    - Hooks bloquent les commits non-conformes
    - Bypass possible avec flag (--no-verify)
    - Documentation dans CONTRIBUTING.md

---

## 💾 PHASE 1 : BACKEND DJANGO SETUP

### 1.1 - Initialisation Django API

- [ ] **TASK-011** [P5] Créer nouveau projet Django avec Django Ninja
  - **Description** : `django-admin startproject ml_core`, configurer Django Ninja API asynchrone
  - **Dépendances** : TASK-001, TASK-003
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django 4.2, Django Ninja, Python 3.13, PostgreSQL
  - **Critères d'acceptation** :
    - Django app générée et démarrée sur localhost:8000
    - Database migrate fonctionne
    - Django Ninja router configuré
    - settings.py avec PostgreSQL + pgvector

- [ ] **TASK-012** [P5] Configurer Celery pour tâches asynchrones
  - **Description** : Setup Celery avec Redis broker, celery beat pour scheduled tasks
  - **Dépendances** : TASK-011
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django, Celery, Redis
  - **Critères d'acceptation** :
    - Celery worker démarre: `celery -A ml_core worker -l info`
    - Tasks s'exécutent async
    - Celery beat pour periodic tasks
    - Retry logic configurée

- [ ] **TASK-013** [P5] Configurer Django Channels pour WebSockets temps réel
  - **Description** : Setup Django Channels, ASGI, WebSocket consumers
  - **Dépendances** : TASK-011
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django, Django Channels, Daphne ASGI
  - **Critères d'acceptation** :
    - WebSocket endpoint /ws/ fonctionne
    - Client peut subscribe à channels (alerts, analytics)
    - Broadcast fonctionne en temps réel
    - Reconnection logic en place

### 1.2 - Database Schema & Models

- [ ] **TASK-014** [P5] Créer migration users & base schema
  - **Description** : Migration Django pour table `users` avec UUID, email unique, timestamps
  - **Dépendances** : TASK-011, TASK-004
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django Migrations, PostgreSQL
  - **Critères d'acceptation** :
    - Table `users` créée via `makemigrations`
    - UUID comme PK
    - Email unique et indexed
    - Timestamps auto-gérés

- [ ] **TASK-015** [P5] Créer User model avec associations
  - **Description** : Django Model User avec validations, ForeignKey/OneToOneField vers data_streams, alerts
  - **Dépendances** : TASK-014
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django Models, ORM
  - **Critères d'acceptation** :
    - Model validé (email presence, format)
    - ForeignKey/reverse relations définies
    - Validators pour soft-delete optionnel

- [ ] **TASK-016** [P5] Créer migration data_streams & modèle
  - **Description** : Migration pour `data_streams` (user_id, source_type, payload JSONB)
  - **Dépendances** : TASK-014
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, PostgreSQL JSONB
  - **Critères d'acceptation** :
    - Table créée avec FK user_id
    - source_type enum ou string
    - JSONB payload flexible
    - Index sur user_id et source_type

- [ ] **TASK-017** [P5] Créer migration document_chunks & indexes HNSW
  - **Description** : Migration pour `document_chunks` avec colonne embedding (vector)
  - **Dépendances** : TASK-016, TASK-004
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, PostgreSQL, pgvector
  - **Critères d'acceptation** :
    - Table créée avec embedding VECTOR(384)
    - HNSW index créé (`CREATE INDEX ON document_chunks USING hnsw`)
    - Requête similarity search fonctionne
    - cluster_category indexed

- [ ] **TASK-018** [P5] Créer migration agent_alerts & modèle
  - **Description** : Migration pour `agent_alerts` (title, description, severity, status, action_payload)
  - **Dépendances** : TASK-014
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, PostgreSQL
  - **Critères d'acceptation** :
    - Table créée avec colonnes requises
    - status enum (pending/acknowledged/executed)
    - severity enum (low/medium/critical)
    - action_payload JSONB flexible

- [ ] **TASK-019** [P5] Créer models pour associations & scopes
  - **Description** : Models DataStream, DocumentChunk, AgentAlert avec associations complètes
  - **Dépendances** : TASK-015, TASK-016, TASK-017, TASK-018
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails Models, ActiveRecord
  - **Critères d'acceptation** :
    - Models avec belongs_to, has_many
    - Scopes utiles (e.g., `pending_alerts`, `critical_alerts`)
    - Validations complètes
    - STI optionnel pour sources

### 1.3 - Authentication & Authorization

- [ ] **TASK-020** [P5] Configurer Django authentication avec JWT tokens
  - **Description** : Installer djangorestframework-simplejwt pour auth API stateless
  - **Dépendances** : TASK-015
  - **Temps estimé** : 4h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django, djangorestframework-simplejwt, JWT
  - **Critères d'acceptation** :
    - POST /api/token/ retourne JWT (access + refresh)
    - POST /api/register/ crée user
    - JWT dans Authorization: Bearer header
    - Refresh token rotation
    - Logout invalidates token

- [ ] **TASK-021** [P5] Configurer Django settings pour JWT secret
  - **Description** : Stocker JWT_SECRET dans .env et settings.py
  - **Dépendances** : TASK-006, TASK-020
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django settings, python-dotenv
  - **Critères d'acceptation** :
    - Secret accessible via `settings.SIMPLE_JWT['SIGNING_KEY']`
    - Différent par environnement (dev/prod)
    - .env pas commité

- [ ] **TASK-022** [P4] Implémenter authorization via Django permissions
  - **Description** : Utiliser Django permissions + custom decorator pour authorization
  - **Dépendances** : TASK-020
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Django, Django Ninja decorators
  - **Critères d'acceptation** :
    - Permissions créées pour User, DataStream, Alert
    - @permission_required decorator en place
    - 403 Forbidden responses

### 1.4 - Core API Endpoints (Django Ninja)

- [ ] **TASK-023** [P5] Créer UsersAPI routes (CRUD)
  - **Description** : GET /api/users/:id, PATCH /api/users/:id, DELETE /api/users/:id
  - **Dépendances** : TASK-015, TASK-020
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django Ninja, Pydantic schemas
  - **Critères d'acceptation** :
    - GET /api/users/:id retourne user JSON
    - PATCH /api/users/:id met à jour profil
    - DELETE /api/users/:id soft-delete
    - 401 sans token, 403 si unauthorized

- [ ] **TASK-024** [P5] Créer DataStreamsAPI (ingestion)
  - **Description** : POST /api/data_streams pour recevoir emails, calendrier, Kijiji payloads
  - **Dépendances** : TASK-016, TASK-020
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django Ninja, Pydantic
  - **Critères d'acceptation** :
    - POST /api/data_streams accepte JSONB payload
    - source_type validé (gmail/kijiji/plaid/google_calendar)
    - Enqueue Celery analysis task
    - 201 avec location header

- [ ] **TASK-025** [P5] Créer DocumentChunksAPI (RAG search)
  - **Description** : GET /api/document_chunks?query=... avec similarity search PostgreSQL pgvector
  - **Dépendances** : TASK-017, TASK-020
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django Ninja, PostgreSQL pgvector, SQLAlchemy
  - **Critères d'acceptation** :
    - GET retourne chunks par similarity
    - Query string avec embedding generation
    - Limit/offset pagination
    - Sorted par cosine_distance

- [ ] **TASK-026** [P5] Créer AlertsAPI (CRUD + actions)
  - **Description** : GET /api/alerts, PATCH /api/alerts/:id (acknowledge/execute), DELETE
  - **Dépendances** : TASK-018, TASK-020
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django Ninja
  - **Critères d'acceptation** :
    - GET /api/alerts filtre par severity/status
    - PATCH change status
    - DELETE soft-delete
    - WebSocket broadcast on change

- [ ] **TASK-027** [P4] Créer Pydantic schemas pour consistent API
  - **Description** : UserSchema, DataStreamSchema, etc. pour validation + serialization
  - **Dépendances** : TASK-023, TASK-024, TASK-025, TASK-026
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Pydantic v2
  - **Critères d'acceptation** :
    - Nested schemas pour relationships
    - Attributes filtrés (pas de secrets)
    - Validators pour business logic

### 1.5 - External Service Integration Layer

- [ ] **TASK-028** [P4] Créer base class pour OAuth clients (Google, Microsoft)
  - **Description** : Base service `OAuthClient` avec refresh_token, validate_token logic
  - **Dépendances** : TASK-020
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Rails, OAuth2 gem
  - **Critères d'acceptation** :
    - Base class initialize(user, service_name)
    - refresh_token method
    - token_valid? check
    - Error handling pour token expiry

- [ ] **TASK-029** [P4] Créer GmailClient service
  - **Description** : Service pour récupérer emails via Gmail API (Net::IMAP + OAuth)
  - **Dépendances** : TASK-028, TASK-024
  - **Temps estimé** : 3h
  - **Priorité** : 4
  - **Tech Stack** : Rails, Gmail API, OAuth2
  - **Critères d'acceptation** :
    - fetch_emails(limit) retourne list
    - Emails parsés en DataStream
    - Error handling pour rate limits
    - Stored credentials utilisés

- [ ] **TASK-030** [P4] Créer CalendarClient service
  - **Description** : Service pour Google Calendar (availability check, event creation)
  - **Dépendances** : TASK-028
  - **Temps estimé** : 3h
  - **Priorité** : 4
  - **Tech Stack** : Rails, Google Calendar API
  - **Critères d'acceptation** :
    - check_availability(date_range) retourne slots
    - create_event(start, end, title, guests)
    - Error handling pour conflicts

- [ ] **TASK-031** [P4] Créer PlaidClient service
  - **Description** : Service pour connecter comptes bancaires via Plaid, récupérer transactions
  - **Dépendances** : TASK-028
  - **Temps estimé** : 3h
  - **Priorité** : 4
  - **Tech Stack** : Rails, Plaid API
  - **Critères d'acceptation** :
    - link_account(link_token) flow
    - get_transactions(account_id)
    - Transaction parsing en DataStream
    - Balance updates en temps réel

- [ ] **TASK-032** [P4] Créer KijijiScraperService (Playwright)
  - **Description** : Service Python pour scraper Kijiji messages, intégré à Rails job
  - **Dépendances** : TASK-024
  - **Temps estimé** : 4h
  - **Priorité** : 4
  - **Tech Stack** : Python, Playwright, Rails Solid Queue
  - **Critères d'acceptation** :
    - Script Python scrape Kijiji headless
    - Messages parsés et pushés à Rails API
    - Rotation de proxies pour éviter blocks
    - Scheduled job toutes les heures

### 1.6 - Background Jobs & Workers (Celery)

- [ ] **TASK-033** [P5] Créer EmailAnalysisTask (enqueue au POST /data_streams)
  - **Description** : Celery task qui analyse email et détermine cluster (recrutement/urgent/finance) via CrewAI
  - **Dépendances** : TASK-012, TASK-024, TASK-072
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Celery, CrewAI, NVIDIA NIM
  - **Critères d'acceptation** :
    - Task enqueue automatiquement après POST
    - CrewAI agent classifie email
    - DocumentChunk créé avec clustering
    - AgentAlert créée si urgent/recrutement

- [ ] **TASK-034** [P5] Créer EmbeddingGenerationTask
  - **Description** : Celery task pour générer embeddings (384-dim) via NVIDIA NIM
  - **Dépendances** : TASK-033, TASK-017
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Celery, NVIDIA NIM API
  - **Critères d'acceptation** :
    - Appel API NVIDIA pour embedding
    - DocumentChunk.embedding mis à jour
    - Batch processing pour performance
    - Retry logic pour timeouts

- [ ] **TASK-035** [P5] Créer AgentExecutionTask (run CrewAI function calls)
  - **Description** : Celery task qui exécute les function calling results (send email, create event, etc.)
  - **Dépendances** : TASK-034, TASK-026
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Celery, CrewAI, OAuth Services
  - **Critères d'acceptation** :
    - Task parse action_payload d'alert
    - Execute API calls (Calendar, Email, etc.) via CrewAI tools
    - Update alert status à executed
    - Error handling + retry

- [ ] **TASK-036** [P4] Créer KijijiScraperTask (recurring)
  - **Description** : Celery beat task qui déclenche script Python scraper Kijiji chaque heure
  - **Dépendances** : TASK-032
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Django, Celery Beat, Cron
  - **Critères d'acceptation** :
    - Task schedule toutes les heures via Celery Beat
    - Appel script Python
    - DataStream créé pour nouveaux messages
    - Error notification si échec

### 1.7 - Django Channels & Real-time Features

- [ ] **TASK-037** [P5] Créer AlertsConsumer (WebSocket real-time)
  - **Description** : Django Channels WebSocket consumer pour broadcast alerts en temps réel
  - **Dépendances** : TASK-013, TASK-026
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django Channels, Daphne
  - **Critères d'acceptation** :
    - Client connect à /ws/alerts/
    - Alert creation broadcast auto
    - Client reçoit updates real-time
    - 0.5-1s latency

- [ ] **TASK-038** [P4] Créer AnalyticsConsumer
  - **Description** : WebSocket consumer pour broadcast financial analytics en temps réel
  - **Dépendances** : TASK-013
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Django Channels
  - **Critères d'acceptation** :
    - Balance updates broadcast
    - Anomaly detection results broadcast
    - Charts updated real-time

- [ ] **TASK-039** [P4] Créer NotificationsConsumer
  - **Description** : WebSocket consumer pour notifications système, statuts Celery tasks
  - **Dépendances** : TASK-013
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : Django Channels
  - **Critères d'acceptation** :
    - Task status updates broadcast
    - System alerts broadcast
    - Toast notifications triggered

### 1.8 - Error Handling & Logging

- [ ] **TASK-040** [P4] Configurer Sentry pour error tracking
  - **Description** : Intégrer sentry-sdk pour capture des errors en prod
  - **Dépendances** : TASK-011
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Django, sentry-sdk
  - **Critères d'acceptation** :
    - Sentry DSN configuré dans settings.py
    - Errors capturés auto
    - Environment context (user, tags)
    - Alertes pour errors critiques

- [ ] **TASK-041** [P4] Configurer Django logging & log rotation
  - **Description** : Setup structured logging (JSON logs), log rotation
  - **Dépendances** : TASK-011
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Django logging, Python json formatter
  - **Critères d'acceptation** :
    - Logs format JSON
    - Rotation daily/weekly
    - Request ID tracking
    - Performance metrics logged

- [ ] **TASK-042** [P4] Créer middleware pour API error responses
  - **Description** : Django middleware pour standardiser format erreurs JSON API
  - **Dépendances** : TASK-011
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Django Middleware
  - **Critères d'acceptation** :
    - Format cohérent {error: {code, message, details}}
    - HTTP status codes corrects
    - Request ID inclus

---

## 🎨 PHASE 2 : FRONTEND REACT 19 SETUP

### 2.1 - Next.js App Setup

- [ ] **TASK-043** [P5] Créer app Next.js 14+ avec App Router
  - **Description** : `npx create-next-app@latest` avec TypeScript, tailwind, ESLint
  - **Dépendances** : TASK-001, TASK-007
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Next.js 14+, React 19, TypeScript
  - **Critères d'acceptation** :
    - App router structuré (app/layout.tsx, app/page.tsx)
    - Tailwind CSS v4 intégré
    - ESLint passe sans errors
    - Dev server démarre sur localhost:3000

- [ ] **TASK-044** [P5] Configurer TypeScript strictement
  - **Description** : Configuration tsconfig.json avec strict: true, lib compatibles
  - **Dépendances** : TASK-043
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : TypeScript
  - **Critères d'acceptation** :
    - tsconfig.json strict: true
    - No any allowed (eslint-plugin-@typescript-eslint)
    - Type checking passe

- [ ] **TASK-045** [P5] Configurer Apollo Client ou TanStack Query
  - **Description** : Setup TanStack Query pour data fetching, caching, mutations
  - **Dépendances** : TASK-043
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19, TanStack Query
  - **Critères d'acceptation** :
    - QueryClient provider en root layout
    - useQuery hooks fonctionne
    - useMutation pour POST/PATCH
    - Caching strategy configurée

- [ ] **TASK-046** [P5] Configurer Zustand pour state management
  - **Description** : Setup Zustand pour global state (user, alerts, filters)
  - **Dépendances** : TASK-043
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19, Zustand
  - **Critères d'acceptation** :
    - Store user state (auth, profile)
    - Store alerts state
    - Persist to localStorage
    - DevTools middleware en dev

### 2.2 - Authentication & Routing

- [ ] **TASK-047** [P5] Créer AuthContext et hooks useAuth
  - **Description** : Context provider pour JWT token, login/logout logic
  - **Dépendances** : TASK-045, TASK-046
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19, Context API
  - **Critères d'acceptation** :
    - useAuth() hook
    - Token stored in localStorage
    - Auto-refresh token logic
    - Logout clears state

- [ ] **TASK-048** [P5] Créer route protégée /dashboard
  - **Description** : Layout pour dashboard, middleware pour check auth
  - **Dépendances** : TASK-047, TASK-043
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Next.js App Router
  - **Critères d'acceptation** :
    - Non-auth redirigé vers /login
    - Dashboard nécessite JWT
    - Loading state while checking auth
    - Logout redirige vers /login

- [ ] **TASK-049** [P5] Créer pages d'authentification (/login, /signup)
  - **Description** : Pages de login/signup avec formulaires, validation
  - **Dépendances** : TASK-047
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19, React Hook Form, Zod
  - **Critères d'acceptation** :
    - Form validation côté client
    - POST /users/sign_up
    - POST /users/sign_in
    - Error messages affichés
    - Loading state pendant request

- [ ] **TASK-050** [P4] Créer route /settings (profil utilisateur)
  - **Description** : Page pour éditer profil, OAuth permissions, preferences
  - **Dépendances** : TASK-047
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : React 19, React Hook Form
  - **Critères d'acceptation** :
    - Affiche profil utilisateur
    - Edit email/name
    - OAuth connections
    - Logout button

### 2.3 - UI Components & Design System

- [ ] **TASK-051** [P5] Configurer Shadcn/ui components
  - **Description** : Installer Button, Card, Input, Select, Dialog, etc.
  - **Dépendances** : TASK-043
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Shadcn/ui, Tailwind CSS
  - **Critères d'acceptation** :
    - Components importables depuis @/components/ui
    - Customization theme tokens
    - Dark mode possible

- [ ] **TASK-052** [P4] Créer component Button primaire/secondaire
  - **Description** : Button component avec variants (primary, secondary, danger)
  - **Dépendances** : TASK-051
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : React, Tailwind CSS
  - **Critères d'acceptation** :
    - Props: variant, size, disabled, loading
    - Loading state avec spinner
    - Accessible (aria-labels)

- [ ] **TASK-053** [P4] Créer component Card réutilisable
  - **Description** : Card avec header, body, footer
  - **Dépendances** : TASK-051
  - **Temps estimé** : 0.5h
  - **Priorité** : 4
  - **Tech Stack** : React, Tailwind
  - **Critères d'acceptation** :
    - Header, body, footer slots
    - Shadow, border, padding customizable
    - Composable

- [ ] **TASK-054** [P4] Créer component Alert/Toast
  - **Description** : Toast notifications (success, error, warning, info)
  - **Dépendances** : TASK-051
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : React 19, Sonner/Framer Motion
  - **Critères d'acceptation** :
    - useToast hook
    - Auto-dismiss après 5s
    - Stack multiple toasts
    - Animations smooth

- [ ] **TASK-055** [P4] Créer component Form avec validation
  - **Description** : Form wrapper avec React Hook Form, Zod validation
  - **Dépendances** : TASK-051
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : React Hook Form, Zod
  - **Critères d'acceptation** :
    - Input components avec error display
    - Server validation error handling
    - Submit handler
    - Reset button

- [ ] **TASK-056** [P4] Créer component Modal/Dialog
  - **Description** : Reusable Modal avec header, body, footer
  - **Dépendances** : TASK-051
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : React, Headless UI
  - **Critères d'acceptation** :
    - Backdrop click closes
    - ESC key closes
    - Focus trap
    - Animated transitions

### 2.4 - Dashboard Layout (Bento Grid)

- [ ] **TASK-057** [P5] Créer layout principal du dashboard
  - **Description** : Structure Bento grid responsive 2-4 colonnes
  - **Dépendances** : TASK-048, TASK-051
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19, Tailwind CSS Grid
  - **Critères d'acceptation** :
    - Layout responsive (mobile, tablet, desktop)
    - Sidebar navigation
    - Top navbar avec user menu
    - Dark mode toggle

- [ ] **TASK-058** [P5] Créer component OmniChat (bloc central)
  - **Description** : Chat input avec voice activation (Whisper API), message history
  - **Dépendances** : TASK-057
  - **Temps estimé** : 4h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19, Web Audio API, Whisper/NVIDIA NIM
  - **Critères d'acceptation** :
    - Text input + Send button
    - Voice recording button (hold to record)
    - Real-time transcription display
    - Message history scrollable
    - WebSocket integration pour responses

- [ ] **TASK-059** [P5] Créer component AlertHub (bloc alertes)
  - **Description** : List d'alertes filtrées par severity, statuts actionables
  - **Dépendances** : TASK-057, TASK-026
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19, TanStack Query
  - **Critères d'acceptation** :
    - GET /alerts fetched
    - Filter par severity/status
    - Click alert → detail view
    - Action buttons (acknowledge, execute)
    - WebSocket real-time updates

- [ ] **TASK-060** [P5] Créer component FinancialAnalytics (bloc patrimoine)
  - **Description** : Chart balance evolution, anomalies d'Isolation Forest
  - **Dépendances** : TASK-057, TASK-024
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19, Recharts
  - **Critères d'acceptation** :
    - LineChart balance over time
    - Anomaly markers en rouge
    - Legend, tooltips
    - Real-time updates via WebSocket
    - Responsive to window resize

- [ ] **TASK-061** [P5] Créer component ActivityMap (bloc services)
  - **Description** : Grille status comptes (Gmail, Calendar, Kijiji, Plaid)
  - **Dépendances** : TASK-057
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19
  - **Critères d'acceptation** :
    - Affiche status connexion par service
    - Derniers messages affichés
    - Click pour ouvrir config OAuth
    - Real-time status updates

### 2.5 - Advanced UI Features

- [ ] **TASK-062** [P4] Implémenter dark mode (Tailwind CSS)
  - **Description** : Theme toggle dark/light avec persistence
  - **Dépendances** : TASK-043
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : Tailwind CSS, React 19
  - **Critères d'acceptation** :
    - Dark mode button en navbar
    - Persistence en localStorage
    - All components support dark
    - Smooth transition

- [ ] **TASK-063** [P4] Implémenter responsive design mobile-first
  - **Description** : Tester responsive sur Mobile/Tablet/Desktop
  - **Dépendances** : TASK-057, TASK-058, TASK-059, TASK-060, TASK-061
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Tailwind CSS, Mobile browsers
  - **Critères d'acceptation** :
    - Dashboard usable sur iPhone 12/14
    - Drawer navigation au lieu de sidebar mobile
    - Touch-friendly buttons (48x48px min)
    - No horizontal scrolling

- [ ] **TASK-064** [P4] Implémenter animations & transitions
  - **Description** : Framer Motion pour entrance, exit, page transitions
  - **Dépendances** : TASK-051
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Framer Motion
  - **Critères d'acceptation** :
    - Page transitions smooth
    - List animations (stagger)
    - Hover effects subtils
    - 60fps performance

- [ ] **TASK-065** [P4] Configurer PWA manifest (offline support optionnel)
  - **Description** : PWA manifest, service worker basic
  - **Dépendances** : TASK-043
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Next.js PWA, Service Workers
  - **Critères d'acceptation** :
    - manifest.json créé
    - Web app installable
    - Offline page shown
    - Icons générés

### 2.6 - WebSocket & Real-time Integration

- [ ] **TASK-066** [P5] Créer WebSocket client pour Action Cable
  - **Description** : Connect à Solid Cable, subscribe à channels
  - **Dépendances** : TASK-045, TASK-013
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19, actioncable package
  - **Critères d'acceptation** :
    - WebSocket connects automatiquement
    - Subscribe à AlertsChannel
    - Message handler reçoit updates
    - Auto-reconnect on disconnect

- [ ] **TASK-067** [P5] Implémenter hook useRealtimeAlerts
  - **Description** : Hook pour subscribe AlertsChannel et update local state
  - **Dépendances** : TASK-066, TASK-045
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React 19 Hooks
  - **Critères d'acceptation** :
    - Hook returns { alerts, loading }
    - Initial fetch + WebSocket updates
    - Cleanup on unmount
    - Optimistic updates possible

- [ ] **TASK-068** [P4] Implémenter hook useRealtimeAnalytics
  - **Description** : Hook pour subscribe AnalyticsChannel
  - **Dépendances** : TASK-066
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : React 19 Hooks
  - **Critères d'acceptation** :
    - Hook returns { balance, anomalies, loading }
    - Real-time chart updates
    - Normalization des données

- [ ] **TASK-069** [P4] Implémenter hook useRealtimeNotifications
  - **Description** : Hook pour subscribe NotificationsChannel, trigger toasts
  - **Dépendances** : TASK-066, TASK-054
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : React 19 Hooks, Sonner
  - **Critères d'acceptation** :
    - Notifications reçues → toast displayed
    - Error notifications rouge
    - Success notifications vert

---

## 🤖 PHASE 3 : MACHINE LEARNING & CLUSTERING (CREWAI + DJANGO)

### 3.1 - CrewAI Integration Infrastructure

- [ ] **TASK-070** [P5] Intégrer CrewAI directement dans Django
  - **Description** : Setup CrewAI agents nativement dans Django (pas microservice externe)
  - **Dépendances** : TASK-001, TASK-003
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django, CrewAI, Python 3.13
  - **Critères d'acceptation** :
    - CrewAI agents importés dans Django
    - /api/health retourne {"status": "ok"}
    - Agents accessible depuis Celery tasks
    - Structured logging JSON

- [ ] **TASK-071** [P5] Configurer connexion PostgreSQL + Django ORM
  - **Description** : SQLAlchemy ORM integration pour queries native Django models
  - **Dépendances** : TASK-070, TASK-004
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django ORM, PostgreSQL
  - **Critères d'acceptation** :
    - Django ORM queries work
    - Connection pooling configured
    - Error handling + retry logic

- [ ] **TASK-072** [P5] Créer service NIM (NVIDIA Inference Microservices) pour CrewAI
  - **Description** : Client OpenAI-compatible pour NVIDIA NIM API utilisé par CrewAI
  - **Dépendances** : TASK-070
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Python, openai library, CrewAI integration
  - **Critères d'acceptation** :
    - OpenAI client initialized with NIM endpoint
    - API key from env
    - Chat completion working
    - CrewAI agents can use NIM models

- [ ] **TASK-073** [P4] Créer service d'embeddings
  - **Description** : Appel NIM pour générer embeddings (384-dim)
  - **Dépendances** : TASK-072
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Python, NIM API
  - **Critères d'acceptation** :
    - Fonction embed_text(text) → vector(384)
    - Batch embedding support
    - Cache possible (Redis optionnel)

### 3.2 - Email Clustering & Classification via CrewAI Agent

- [ ] **TASK-074** [P5] Créer CrewAI Agent Email Classifier
  - **Description** : Agent CrewAI qui classifie emails via NIM, retourne category + entities
  - **Dépendances** : TASK-072
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : CrewAI, Python, NIM API
  - **Critères d'acceptation** :
    - Agent classifie email → "recrutement" | "urgent" | "finance" | "normal"
    - Prompt bien structuré
    - Confidence score + entities extracted
    - Tests cases couverts

- [ ] **TASK-075** [P5] Créer entity extractor pour emails (sender, date, objet)
  - **Description** : Extraction entities from email body
  - **Dépendances** : TASK-072
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Python, NIM API, spaCy optionnel
  - **Critères d'acceptation** :
    - extract_entities(email) → {sender, dates, subjects, amounts}
    - Regex + NLP combination
    - JSON output

- [ ] **TASK-076** [P5] Créer endpoint POST /analyze_email
  - **Description** : Endpoint FastAPI qui analyse email et retourne clusters + entities
  - **Dépendances** : TASK-074, TASK-075, TASK-070
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : FastAPI, Python
  - **Critères d'acceptation** :
    - Accepts POST {email_text, email_id}
    - Returns {category, entities, confidence}
    - Stores result in document_chunks

- [ ] **TASK-077** [P4] Créer endpoint POST /chunk_email (RAG)
  - **Description** : Endpoint pour chunker long emails (sliding window)
  - **Dépendances** : TASK-076
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : FastAPI, Python
  - **Critères d'acceptation** :
    - Chunks sized 500-1000 tokens
    - Sliding window overlap 10%
    - Returns list of chunks

### 3.3 - Anomaly Detection (Isolation Forest)

- [ ] **TASK-078** [P5] Créer model Isolation Forest pour transactions
  - **Description** : Train/test anomaly detection sur transactions Plaid
  - **Dépendances** : TASK-071
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Python, Scikit-Learn, Pandas
  - **Critères d'acceptation** :
    - Features: amount, merchant_category, day_of_week, time_of_day
    - Model serialized (pickle/joblib)
    - Anomaly score per transaction
    - 80%+ specificity target

- [ ] **TASK-079** [P5] Créer endpoint POST /detect_anomalies
  - **Description** : Endpoint pour detect anomalies dans list transactions
  - **Dépendances** : TASK-078
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : FastAPI, Scikit-Learn
  - **Critères d'acceptation** :
    - Accepts {transactions: [{amount, merchant, timestamp}]}
    - Returns {anomalies: [indices], scores}
    - Confidence threshold configurable

- [ ] **TASK-080** [P4] Créer matrix Pearson correlations pour financials
  - **Description** : Compute correlation matrix pour detect patterns (e.g., duplicate subs)
  - **Dépendances** : TASK-071
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Python, Pandas, NumPy
  - **Critères d'acceptation** :
    - Pearson correlation computed
    - Subscriptions grouped by pattern
    - Duplicates identified (>95% similarity)

- [ ] **TASK-081** [P4] Créer endpoint POST /financial_insights
  - **Description** : Endpoint pour insights financiers (anomalies + patterns)
  - **Dépendances** : TASK-079, TASK-080
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : FastAPI
  - **Critères d'acceptation** :
    - Returns {anomalies, duplicate_subscriptions, trends}
    - JSON structured clearly
    - Cached per user for 1h

### 3.4 - Kijiji Message Analysis

- [ ] **TASK-082** [P4] Créer classifier pour Kijiji messages
  - **Description** : Classifier messages Kijiji (negotiation/spam/genuine)
  - **Dépendances** : TASK-072
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Python, NIM API
  - **Critères d'acceptation** :
    - classify_kijiji_message(text) → category
    - Tags common patterns (lowballing, spam)

- [ ] **TASK-083** [P4] Créer endpoint POST /analyze_kijiji_message
  - **Description** : Endpoint pour analyser Kijiji messages
  - **Dépendances** : TASK-082
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : FastAPI
  - **Critères d'acceptation** :
    - Accepts message text
    - Returns classification + suggested response template

### 3.5 - Vector Search & RAG

- [ ] **TASK-084** [P5] Créer endpoint POST /search_documents
  - **Description** : Similarity search via PostgreSQL pgvector
  - **Dépendances** : TASK-071, TASK-073
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : FastAPI, PostgreSQL, pgvector
  - **Critères d'acceptation** :
    - Accepts {query_text, limit, threshold}
    - Generate embedding for query
    - Cosine similarity search
    - Returns top-k documents

- [ ] **TASK-085** [P5] Créer endpoint POST /rag_context
  - **Description** : Retrieve context documents pour LLM function calling
  - **Dépendances** : TASK-084, TASK-072
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : FastAPI, PostgreSQL
  - **Critères d'acceptation** :
    - Returns ranked documents for context
    - Limit total tokens to 4000
    - Source metadata included

- [ ] **TASK-086** [P4] Créer batch embedding job
  - **Description** : Batch process nouveaux documents pour embeddings
  - **Dépendances** : TASK-073
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Python, Pandas
  - **Critères d'acceptation** :
    - Process batches of 50 at a time
    - Avoid API rate limits
    - Upsert to document_chunks

---

## 🌐 PHASE 4 : INTÉGRATIONS EXTERNES

### 4.1 - Gmail Integration (OAuth + Ingestion)

- [ ] **TASK-087** [P5] Configurer Google OAuth flow (Rails Devise)
  - **Description** : Intégrer OmniAuth Google pour login + permissions email
  - **Dépendances** : TASK-020, TASK-047
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails Devise, OmniAuth, Google API
  - **Critères d'acceptation** :
    - OAuth redirect flow works
    - User created/linked automatiquement
    - Email scope requested
    - Refresh token stored encrypted

- [ ] **TASK-088** [P5] Créer GmailSyncJob pour sync emails
  - **Description** : Background job pour fetch emails via Gmail API
  - **Dépendances** : TASK-029, TASK-012
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, Gmail API
  - **Critères d'acceptation** :
    - Fetch unread emails
    - Parse headers (From, Subject, Date, Body)
    - Create DataStream entries
    - Enqueue EmailAnalysisJob
    - Handle rate limits

- [ ] **TASK-089** [P5] Créer service pour send email replies
  - **Description** : Service qui envoie réponses via Gmail API
  - **Dépendances** : TASK-029, TASK-035
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, Gmail API
  - **Critères d'acceptation** :
    - send_reply_email(to, subject, body, thread_id)
    - Message formatted proprement
    - Success/error handling

- [ ] **TASK-090** [P4] Créer endpoint React pour trigger sync Gmail
  - **Description** : Frontend button pour manual Gmail sync
  - **Dépendances** : TASK-049, TASK-088
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : React, TanStack Query
  - **Critères d'acceptation** :
    - Button dans settings
    - Loading state + success toast
    - Error handling

### 4.2 - Google Calendar Integration

- [ ] **TASK-091** [P5] Configurer Google Calendar API permissions
  - **Description** : Setup OAuth scope calendar.events, calendar.readonly
  - **Dépendances** : TASK-087
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Google API, OAuth
  - **Critères d'acceptation** :
    - Calendar scope added to OAuth
    - Incremental consent flow
    - Token scopes documented

- [ ] **TASK-092** [P5] Créer CalendarSyncJob
  - **Description** : Job para sincronizar Google Calendar events
  - **Dépendances** : TASK-030, TASK-012
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, Google Calendar API
  - **Critères d'acceptation** :
    - Fetch events for next 7 days
    - Check availability slots
    - Store in cache (Redis optional)

- [ ] **TASK-093** [P5] Créer service create_calendar_event
  - **Description** : Service pour créer events dans Google Calendar
  - **Dépendances** : TASK-030, TASK-035
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, Google Calendar API
  - **Critères d'acceptation** :
    - create_event(title, start, end, guests)
    - Attendees notifiés
    - Return calendar event ID

- [ ] **TASK-094** [P4] Créer service Teams meeting creation
  - **Description** : Service créer Teams meetings via Microsoft Graph
  - **Dépendances** : TASK-030
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Rails, Microsoft Graph API
  - **Critères d'acceptation** :
    - create_teams_meeting(title, start, end, guests)
    - Meeting link générée
    - Attendees notifiés

- [ ] **TASK-095** [P4] Créer calendrier widget React
  - **Description** : Component pour afficher calendar dans dashboard
  - **Dépendances** : TASK-061
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : React, react-calendar
  - **Critères d'acceptation** :
    - Mini calendar widget
    - Availability highlighted
    - Click to show event details

### 4.3 - Plaid Integration (Banking Data)

- [ ] **TASK-096** [P5] Configurer Plaid Link flow
  - **Description** : Setup Plaid API keys, Plaid Link widget
  - **Dépendances** : TASK-001
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Plaid API, React Plaid Link
  - **Critères d'acceptation** :
    - API keys stored in Rails credentials
    - Link token endpoint created
    - React component renders Plaid Link

- [ ] **TASK-097** [P5] Créer PlaidLinkController (Rails)
  - **Description** : Endpoint pour exchange_public_token, store access_token
  - **Dépendances** : TASK-096
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, Plaid API
  - **Critères d'acceptation** :
    - POST /plaid/link_token
    - POST /plaid/exchange_token
    - access_token encrypted in DB
    - Item ID stored

- [ ] **TASK-098** [P5] Créer PlaidSyncJob
  - **Description** : Job para sync transactions from Plaid
  - **Dépendances** : TASK-012, TASK-097, TASK-031
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, Plaid API
  - **Critères d'acceptation** :
    - get_transactions(last 30 days)
    - Parse transactions (amount, merchant, category, date)
    - Create DataStream entries
    - Enqueue financial analysis

- [ ] **TASK-099** [P5] Créer AccountsController (list connected accounts)
  - **Description** : GET /plaid/accounts retourne liste accounts connectés
  - **Dépendances** : TASK-097
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, Plaid API
  - **Critères d'acceptation** :
    - Retourne {accounts: [{id, name, balance, type}]}
    - Cached per user

- [ ] **TASK-100** [P4] Créer React component Plaid Link modal
  - **Description** : Modal pour connecter compte bancaire
  - **Dépendances** : TASK-049, TASK-096
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : React, Plaid Link
  - **Critères d'acceptation** :
    - Button "Connect Bank Account"
    - Modal opens Plaid Link
    - Success → refresh accounts list

- [ ] **TASK-101** [P4] Créer React component Accounts listing
  - **Description** : Component liste accounts bancaires avec balance
  - **Dépendances** : TASK-061, TASK-099
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : React, TanStack Query
  - **Critères d'acceptation** :
    - Affiche tous accounts
    - Real-time balance updates
    - Disconnect button possible

### 4.4 - Kijiji Scraping (Playwright)

- [ ] **TASK-102** [P5] Créer Python script Kijiji scraper (Playwright)
  - **Description** : Headless browser automation pour scraper Kijiji messages
  - **Dépendances** : TASK-070
  - **Temps estimé** : 4h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Python, Playwright, requests
  - **Critères d'acceptation** :
    - Login to Kijiji
    - Scrape inbox messages
    - Parse sender, message, price offer, timestamp
    - Return JSON list

- [ ] **TASK-103** [P5] Créer endpoint Rails pour webhook Kijiji scraper
  - **Description** : Endpoint POST /data_streams/kijiji pour receive scraped data
  - **Dépendances** : TASK-024
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails
  - **Critères d'acceptation** :
    - Accept scraped Kijiji data
    - Create DataStream entries
    - Enqueue analysis

- [ ] **TASK-104** [P5] Créer KijijiScraperJob (recurring)
  - **Description** : Job qui déclenche script scraper toutes les heures
  - **Dépendances** : TASK-036, TASK-102
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails Solid Queue, Python
  - **Critères d'acceptation** :
    - Job execute toutes les heures
    - Script stdout captured
    - Errors logged + notified
    - Rotation de proxies

- [ ] **TASK-105** [P4] Créer React component Kijiji messages view
  - **Description** : Component affiche derniers messages Kijiji
  - **Dépendances** : TASK-061, TASK-024
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : React, TanStack Query
  - **Critères d'acceptation** :
    - List derniers messages
    - Grouper par item listing
    - Reply button (draft)

---

## 🔌 PHASE 5 : FEATURES AGENTS & WORKFLOWS

### 5.1 - Agent CrewAI Integration

- [ ] **TASK-106** [P5] Implémenter CrewAI agents orchestration
  - **Description** : 3 agents CrewAI (Email Classifier, Financial Auditor, Kijiji Negotiator) avec tools déclarés
  - **Dépendances** : TASK-011, TASK-072
  - **Temps estimé** : 4h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : CrewAI, Django integration
  - **Critères d'acceptation** :
    - Agents registry JSON structure
    - check_calendar_availability tool déclare parameters
    - send_reply_email tool défini
    - create_teams_meeting tool déclaré

- [ ] **TASK-107** [P5] Créer AgentCommandService (CrewAI + NIM)
  - **Description** : Service Django qui envoie command+context à CrewAI agents, parse tool_calls
  - **Dépendances** : TASK-106, TASK-072
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django, CrewAI
  - **Critères d'acceptation** :
    - accepts(command, context_documents, available_tools)
    - CrewAI agents avec NIM models
    - Parse tool_calls from response
    - JSON structured results

- [ ] **TASK-108** [P5] Créer ToolExecutor (exécute les function calls)
  - **Description** : Service qui exécute les tools appelés par IA
  - **Dépendances** : TASK-107, TASK-089, TASK-093
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails
  - **Critères d'acceptation** :
    - execute_tools(tool_calls) → results
    - Dispatch to respective services
    - Error handling + retry
    - Result formatting

- [ ] **TASK-109** [P5] Créer MessagesAPI pour chat Django
  - **Description** : POST /api/messages endpoint pour recevoir user commands + CrewAI execution
  - **Dépendances** : TASK-107
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django Ninja, Django Channels
  - **Critères d'acceptation** :
    - POST /api/messages {content, alert_id}
    - Enqueue Celery agent execution task
    - Return streaming response via WebSocket
    - Save message history

- [ ] **TASK-110** [P5] Créer AgentExecutionTask (streaming responses)
  - **Description** : Celery task qui exécute commandes CrewAI avec streaming
  - **Dépendances** : TASK-012, TASK-107, TASK-108
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Celery, CrewAI, Django Channels
  - **Critères d'acceptation** :
    - Fetch context documents (RAG)
    - Call CrewAI agent
    - Execute CrewAI tools
    - Stream response chunks via WebSocket
    - Store final message

### 5.2 - Voice Command Integration

- [ ] **TASK-111** [P5] Intégrer Whisper API pour speech-to-text
  - **Description** : Endpoint Django pour transcription voice → text via NVIDIA NIM
  - **Dépendances** : TASK-109
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django Ninja, NVIDIA NIM / OpenAI Whisper
  - **Critères d'acceptation** :
    - POST /api/transcribe {audio_blob}
    - Return transcription text
    - Support multiple languages
    - Real-time streaming optional

- [ ] **TASK-112** [P5] Créer Web Audio API recording (React)
  - **Description** : Component React pour record voice input
  - **Dépendances** : TASK-058
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React, Web Audio API
  - **Critères d'acceptation** :
    - Press & hold button to record
    - Real-time waveform visualization
    - Release to stop + transcribe
    - Error handling (no microphone)

- [ ] **TASK-113** [P4] Créer voice response (text-to-speech)
  - **Description** : TTS endpoint pour agent responses
  - **Dépendances** : TASK-111
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Rails, NVIDIA NIM TTS
  - **Critères d'acceptation** :
    - POST /text_to_speech {text, language}
    - Return audio_url or audio_blob
    - Voice selection optional

### 5.3 - Smart Workflows

- [ ] **TASK-114** [P5] Créer workflow "Confirm RDV" (booking confirmation)
  - **Description** : Workflow multi-step pour confirmer rendez-vous
  - **Dépendances** : TASK-107, TASK-093
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, YAML workflows
  - **Critères d'acceptation** :
    - Detect RDV proposal in email
    - Check calendar availability
    - Generate confirmation draft
    - Send email + create calendar event
    - User can review before execute

- [ ] **TASK-115** [P5] Créer workflow "Financial Anomaly Alert"
  - **Description** : Workflow pour détecter + notifier anomalies financières
  - **Dépendances** : TASK-079, TASK-081
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, Python ML
  - **Critères d'acceptation** :
    - Run monthly anomaly detection
    - Create alerts for duplicates/anomalies
    - Suggest actions (cancel subscription, etc.)

- [ ] **TASK-116** [P4] Créer workflow "Email Auto-Reply"
  - **Description** : Workflow pour auto-reply à certain patterns
  - **Dépendances** : TASK-107, TASK-089
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Rails
  - **Critères d'acceptation** :
    - Define auto-reply rules (sender, keywords)
    - Generate smart response
    - Send via Gmail API
    - Audit trail

- [ ] **TASK-117** [P4] Créer workflow "Kijiji Negotiation"
  - **Description** : Workflow pour assister négociation Kijiji
  - **Dépendances** : TASK-082, TASK-083
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Rails, Python ML
  - **Critères d'acceptation** :
    - Analyze incoming offer
    - Compare to historical data
    - Suggest counter-offer
    - Generate response draft

### 5.4 - Notification & Alert Management

- [ ] **TASK-118** [P5] Créer notification preferences UI
  - **Description** : React page pour configurer notification channels
  - **Dépendances** : TASK-049, TASK-054
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : React, TanStack Query
  - **Critères d'acceptation** :
    - Toggle email notifications
    - Toggle in-app notifications
    - Set frequency (real-time, daily, etc.)
    - Save preferences

- [ ] **TASK-119** [P5] Créer alert severity + priority rules
  - **Description** : Admin interface pour configure alert routing + priorities
  - **Dépendances** : TASK-026
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, React
  - **Critères d'acceptation** :
    - Rule builder UI
    - Alert classification rules
    - Priority assignment
    - Save rules to database

- [ ] **TASK-120** [P4] Créer email notification sending (NotificationJob)
  - **Description** : Job pour envoyer notifications via email
  - **Dépendances** : TASK-012, TASK-089
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Rails, SendGrid/AWS SES
  - **Critères d'acceptation** :
    - Template-based emails
    - User preferences respected
    - Unsubscribe link
    - Reply-to configured

---

## 🧪 PHASE 6 : TESTS & OPTIMISATION

### 6.1 - Backend Testing

- [ ] **TASK-121** [P5] Configurer Pytest pour Django
  - **Description** : Setup Pytest avec pytest-django, factories, mocking
  - **Dépendances** : TASK-011
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Pytest, pytest-django, factory-boy, Faker
  - **Critères d'acceptation** :
    - Test suite structure
    - Example helper fixtures
    - Database fixture configured

- [ ] **TASK-122** [P5] Écrire unit tests pour Models
  - **Description** : Couvrir model validations, relationships, managers
  - **Dépendances** : TASK-121, TASK-019
  - **Temps estimé** : 4h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Pytest, pytest-django
  - **Critères d'acceptation** :
    - Models User, DataStream, Alert, DocumentChunk
    - >80% code coverage
    - Edge cases couverts

- [ ] **TASK-123** [P5] Écrire tests pour API endpoints
  - **Description** : Test tous endpoints (GET, POST, PATCH, DELETE)
  - **Dépendances** : TASK-121, TASK-023, TASK-024, TASK-025, TASK-026
  - **Temps estimé** : 6h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Pytest, Django test client
  - **Critères d'acceptation** :
    - Success status codes 200/201
    - Error status codes 4xx/5xx
    - Response schema validation (Pydantic)
    - Auth required tests

- [ ] **TASK-124** [P4] Écrire integration tests pour Celery tasks
  - **Description** : Test Celery tasks complets (async execution)
  - **Dépendances** : TASK-121, TASK-033, TASK-034, TASK-035
  - **Temps estimé** : 3h
  - **Priorité** : 4
  - **Tech Stack** : Pytest, pytest-celery
  - **Critères d'acceptation** :
    - EmailAnalysisTask complete flow
    - EmbeddingGenerationTask tested
    - Error retry logic tested

- [ ] **TASK-125** [P4] Écrire service specs pour OAuth/external APIs
  - **Description** : Test OAuth services avec mocked API responses
  - **Dépendances** : TASK-121, TASK-028, TASK-029, TASK-030, TASK-031
  - **Temps estimé** : 3h
  - **Priorité** : 4
  - **Tech Stack** : RSpec, WebMock/VCR
  - **Critères d'acceptation** :
    - GmailClient spec
    - CalendarClient spec
    - PlaidClient spec
    - Error handling tested

- [ ] **TASK-126** [P4] Configurer coverage reporting (SimpleCov)
  - **Description** : Setup code coverage badge, CI check pour >80%
  - **Dépendances** : TASK-121
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : SimpleCov, CodeClimate
  - **Critères d'acceptation** :
    - Coverage report generated
    - CI fails if <80% coverage
    - Badge affichée dans README

### 6.2 - Frontend Testing

- [ ] **TASK-127** [P5] Configurer Vitest + React Testing Library
  - **Description** : Setup unit tests pour React components
  - **Dépendances** : TASK-043
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Vitest, React Testing Library
  - **Critères d'acceptation** :
    - Vitest config
    - Example test file
    - Setup/teardown helpers

- [ ] **TASK-128** [P5] Écrire component tests pour core components
  - **Description** : Test rendering, interactions, state changes
  - **Dépendances** : TASK-127, TASK-051, TASK-052, TASK-053, TASK-054, TASK-055
  - **Temps estimé** : 4h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Vitest, React Testing Library
  - **Critères d'acceptation** :
    - Button component renders
    - Input changes state
    - Form submission
    - >70% component coverage

- [ ] **TASK-129** [P5] Écrire hook tests (useAuth, useRealtimeAlerts)
  - **Description** : Test custom hooks avec renderHook
  - **Dépendances** : TASK-127, TASK-047, TASK-067
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Vitest, renderHook
  - **Critères d'acceptation** :
    - useAuth hook tested
    - useRealtimeAlerts tested
    - State updates tested

- [ ] **TASK-130** [P4] Configurer Playwright pour E2E tests
  - **Description** : Setup E2E testing framework
  - **Dépendances** : TASK-043
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Playwright, Node.js
  - **Critères d'acceptation** :
    - Playwright config
    - Example test files
    - CI integration

- [ ] **TASK-131** [P4] Écrire E2E tests pour critical flows
  - **Description** : Test login, alert interaction, message sending
  - **Dépendances** : TASK-130
  - **Temps estimé** : 3h
  - **Priorité** : 4
  - **Tech Stack** : Playwright
  - **Critères d'acceptation** :
    - Login flow E2E test
    - Create alert test
    - Send message test
    - 3+ critical paths

- [ ] **TASK-132** [P4] Configurer Percy/Chromatic para visual regression
  - **Description** : Visual regression testing pour component changes
  - **Dépendances** : TASK-127
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Percy/Chromatic
  - **Critères d'acceptation** :
    - Screenshots baseline
    - CI regression check
    - PR visual review

### 6.3 - Python ML Testing

- [ ] **TASK-133** [P4] Écrire Pytest tests pour ML services
  - **Description** : Test classifier, embedder, anomaly detection
  - **Dépendances** : TASK-070, TASK-074, TASK-078
  - **Temps estimé** : 3h
  - **Priorité** : 4
  - **Tech Stack** : Pytest
  - **Critères d'acceptation** :
    - classify_email tested
    - embed_text tested
    - anomaly detection tested
    - Edge cases handled

- [ ] **TASK-134** [P4] Créer fixtures de test données
  - **Description** : Sample emails, transactions pour tests
  - **Dépendances** : TASK-133
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Pytest fixtures
  - **Critères d'acceptation** :
    - Sample email JSON
    - Sample transactions
    - Fixtures importables

### 6.4 - Performance Optimization

- [ ] **TASK-135** [P5] Optimiser database queries (N+1 prevention)
  - **Description** : Audit queries, add includes/joins, optimize indexes
  - **Dépendances** : TASK-122, TASK-123
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, PostgreSQL
  - **Critères d'acceptation** :
    - Query time <100ms pour /alerts
    - DocumentChunk search <500ms
    - No N+1 queries
    - Bullet gem clean

- [ ] **TASK-136** [P5] Configurer Redis caching
  - **Description** : Add Redis for session, query caching
  - **Dépendances** : TASK-011, TASK-003
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Redis, Rails cache
  - **Critères d'acceptation** :
    - Redis configured
    - Cache strategy defined
    - TTLs configured
    - Docker redis service

- [ ] **TASK-137** [P5] Implémenter API response caching
  - **Description** : HTTP cache headers, ETag generation
  - **Dépendances** : TASK-136
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, HTTP headers
  - **Critères d'acceptation** :
    - Cache-Control headers set
    - ETag generation
    - 304 Not Modified responses

- [ ] **TASK-138** [P4] Optimiser React bundle size
  - **Description** : Code splitting, lazy loading, tree-shaking
  - **Dépendances** : TASK-043
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : Next.js, webpack
  - **Critères d'acceptation** :
    - Bundle <100KB gzipped
    - Lazy load routes
    - Dynamic imports for charts

- [ ] **TASK-139** [P4] Optimiser image assets
  - **Description** : Compress images, WebP format, responsive sizes
  - **Dépendances** : TASK-043
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : Next.js Image component
  - **Critères d'acceptation** :
    - WebP generation
    - Responsive sizes
    - CDN serving

- [ ] **TASK-140** [P4] Configurer CDN pour static assets (Cloudflare)
  - **Description** : Setup CDN caching, cache busting
  - **Dépendances** : TASK-043
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Cloudflare
  - **Critères d'acceptation** :
    - CDN configured
    - Cache headers set
    - Cache busting working

### 6.5 - Security & Penetration Testing

- [ ] **TASK-141** [P5] Configurer Django security checks
  - **Description** : Setup Django security checks + bandit pour code scanning
  - **Dépendances** : TASK-011
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Django, bandit
  - **Critères d'acceptation** :
    - `python manage.py check --deploy` passes
    - Bandit runs in CI
    - No high-severity issues
    - False positives documented

- [ ] **TASK-142** [P5] Audit JWT token security
  - **Description** : Validate token expiry, secret rotation
  - **Dépendances** : TASK-020
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails, JWT
  - **Critères d'acceptation** :
    - Token expiry 24h
    - Refresh token logic
    - No token leaks
    - HTTPS only

- [ ] **TASK-143** [P4] Test CORS configuration
  - **Description** : Ensure CORS headers restrict properly
  - **Dépendances** : TASK-011
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : Rails, CORS
  - **Critères d'acceptation** :
    - Only React domain allowed
    - Credentials included properly
    - Preflight works

- [ ] **TASK-144** [P4] Test OAuth token refresh security
  - **Description** : Validate refresh token rotation, expiry
  - **Dépendances** : TASK-087
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Rails, OAuth2
  - **Critères d'acceptation** :
    - Refresh token rotates
    - Old tokens invalidated
    - No refresh token reuse

---

## 🚀 PHASE 7 : DÉPLOIEMENT & DOCUMENTATION

### 7.1 - Deployment Infrastructure

- [ ] **TASK-145** [P5] Configurer Dockerfile production
  - **Description** : Multi-stage build, minimal image size
  - **Dépendances** : TASK-003, TASK-011, TASK-043, TASK-070
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Docker
  - **Critères d'acceptation** :
    - Rail Dockerfile <500MB
    - React build Dockerfile <200MB
    - Python ML Dockerfile <300MB
    - Docker build works locally

- [ ] **TASK-146** [P5] Configurer docker-compose production
  - **Description** : Production compose with healthchecks, restart policies
  - **Dépendances** : TASK-145, TASK-003
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Docker Compose
  - **Critères d'acceptation** :
    - All services in docker-compose.yml
    - Healthchecks configured
    - Restart: always
    - Resource limits set

- [ ] **TASK-147** [P5] Configurer Kubernetes deployment (ou Cloud Run)
  - **Description** : Helm charts, Ingress, Service definitions
  - **Dépendances** : TASK-145, TASK-146
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Kubernetes, Helm (optionnel: GCP Cloud Run)
  - **Critères d'acceptation** :
    - Helm chart créé
    - Ingress configured
    - Rolling updates working
    - Database persistence

- [ ] **TASK-148** [P5] Configurer CI/CD pipeline (GitHub Actions)
  - **Description** : Build, test, deploy on push/PR
  - **Dépendances** : TASK-002, TASK-121, TASK-127
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : GitHub Actions, Docker
  - **Critères d'acceptation** :
    - Lint jobs pass
    - Test jobs pass
    - Build docker images
    - Push to registry
    - Deploy to staging

- [ ] **TASK-149** [P5] Configurer monitoring & alerting (Prometheus + Grafana)
  - **Description** : Metrics exposition, dashboards, alerts
  - **Dépendances** : TASK-011, TASK-070
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Prometheus, Grafana, Rails/FastAPI metrics
  - **Critères d'acceptation** :
    - Rails /metrics endpoint
    - Python /metrics endpoint
    - Prometheus scraping
    - Grafana dashboards
    - Alert thresholds configured

- [ ] **TASK-150** [P5] Configurer log centralization (ELK ou Loki)
  - **Description** : Centralized logging, searchable, queryable
  - **Dépendances** : TASK-041
  - **Temps estimé** : 2.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Elasticsearch/Logstash/Kibana ou Loki/Promtail/Grafana
  - **Critères d'acceptation** :
    - Logs collected from all services
    - Searchable by timestamp/level/component
    - Dashboards created
    - Retention policy set

### 7.2 - Production Database & Migration

- [ ] **TASK-151** [P5] Configurer PostgreSQL production (RDS ou self-hosted)
  - **Description** : High-availability setup, backups, replicas
  - **Dépendances** : TASK-004, TASK-011
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : PostgreSQL, AWS RDS / GCP Cloud SQL
  - **Critères d'acceptation** :
    - Production RDS instance
    - Multi-AZ enabled
    - Automated backups daily
    - Read replicas optional
    - Restore tested

- [ ] **TASK-152** [P5] Créer migration strategy (zero-downtime)
  - **Description** : Blue-green deployment, backward-compatible migrations
  - **Dépendances** : TASK-011, TASK-148
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails migrations, Kuberentes
  - **Critères d'acceptation** :
    - Migration guide documented
    - Backward compatibility tested
    - Rollback procedure ready
    - Zero-downtime possible

- [ ] **TASK-153** [P4] Configurer database seeding (production data)
  - **Description** : Seeds pour données initiales, test users, config
  - **Dépendances** : TASK-011, TASK-151
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Rails seeds
  - **Critères d'acceptation** :
    - db/seeds.rb created
    - Admin user created
    - Sample data seeded
    - Safe to run multiple times

### 7.3 - Secrets & SSL/TLS Management

- [ ] **TASK-154** [P5] Configurer SSL/TLS certificates (Let's Encrypt)
  - **Description** : HTTPS setup, certificate renewal automation
  - **Dépendances** : TASK-146
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Let's Encrypt, cert-manager (K8s) ou nginx
  - **Critères d'acceptation** :
    - HTTPS enabled
    - Certificate renewal automated
    - HSTS headers set
    - Mixed content warnings none

- [ ] **TASK-155** [P5] Configurer secrets management (HashiCorp Vault ou AWS Secrets Manager)
  - **Description** : Centralized secret rotation, encryption
  - **Dépendances** : TASK-006, TASK-146
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Vault / AWS Secrets Manager
  - **Critères d'acceptation** :
    - All secrets in vault
    - Rotation policy defined
    - Audit logging enabled
    - Backup tested

- [ ] **TASK-156** [P5] Implémenter database encryption at rest
  - **Description** : Enable encryption for RDS, EBS volumes
  - **Dépendances** : TASK-151, TASK-154
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : AWS KMS / GCP Cloud KMS
  - **Critères d'acceptation** :
    - Database encryption enabled
    - Keys managed
    - Performance impact minimal

### 7.4 - Monitoring & Incident Response

- [ ] **TASK-157** [P5] Configurer alerting (PagerDuty intégration)
  - **Description** : Critical alerts → PagerDuty notifications
  - **Dépendances** : TASK-149, TASK-040
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : PagerDuty, Alertmanager
  - **Critères d'acceptation** :
    - PagerDuty integration
    - Alert routing configured
    - On-call schedule set
    - Escalation policy defined

- [ ] **TASK-158** [P5] Créer runbook incidents (documentation)
  - **Description** : Incident response procedures, escalation paths
  - **Dépendances** : TASK-157
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Markdown documentation
  - **Critères d'acceptation** :
    - High memory alert runbook
    - Database connection failure runbook
    - API down runbook
    - Rollback procedures

- [ ] **TASK-159** [P4] Configurer APM (Application Performance Monitoring)
  - **Description** : New Relic / DataDog / Datadog agent
  - **Dépendances** : TASK-011, TASK-070, TASK-043
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : New Relic / DataDog
  - **Critères d'acceptation** :
    - APM agent installed
    - Transactions tracked
    - Custom metrics defined
    - Alerts on anomalies

### 7.5 - Documentation

- [ ] **TASK-160** [P5] Écrire API documentation (OpenAPI/Swagger)
  - **Description** : Automatic API docs from Rails controllers
  - **Dépendances** : TASK-023, TASK-024, TASK-025, TASK-026
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Swagger UI, Rswag gem
  - **Critères d'acceptation** :
    - All endpoints documented
    - Request/response schemas
    - Authentication explained
    - Swagger UI accessible

- [ ] **TASK-161** [P5] Écrire README.md project overview
  - **Description** : Quick start, architecture overview, deployment
  - **Dépendances** : TASK-001
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Markdown
  - **Critères d'acceptation** :
    - What is JARVIS OMNISCIENT
    - Tech stack listed
    - Local setup instructions
    - Deployment instructions
    - Contributing guidelines

- [ ] **TASK-162** [P5] Écrire Architecture.md documentation
  - **Description** : System design, data flow, component interactions
  - **Dépendances** : TASK-001, TASK-057
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Markdown, Diagrams
  - **Critères d'acceptation** :
    - System architecture diagram
    - Data flow diagrams
    - Component responsibilities
    - Database schema documentation

- [ ] **TASK-163** [P5] Écrire Developer Guide
  - **Description** : How to setup dev environment, Django code style, branching
  - **Dépendances** : TASK-001, TASK-008, TASK-009, TASK-010
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Markdown
  - **Critères d'acceptation** :
    - Dev environment setup (Django + Celery + CrewAI)
    - Code style guide (Black, isort)
    - Git branching strategy
    - Testing requirements (Pytest)
    - PR checklist

- [ ] **TASK-164** [P5] Écrire Deployment Guide
  - **Description** : Step-by-step production deployment procedures
  - **Dépendances** : TASK-147, TASK-152
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Markdown
  - **Critères d'acceptation** :
    - Prerequisites listed
    - Step-by-step deployment
    - Rollback procedure
    - Verification checklist

- [ ] **TASK-165** [P5] Écrire Operations Guide
  - **Description** : Monitoring, logging, scaling, backup procedures
  - **Dépendances** : TASK-149, TASK-150, TASK-157
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Markdown
  - **Critères d'acceptation** :
    - Monitoring dashboard walkthrough
    - Log analysis procedures
    - Scaling guidelines
    - Backup/restore procedures

- [ ] **TASK-166** [P4] Créer API client library (SDK optionnel)
  - **Description** : Npm package pour client API
  - **Dépendances** : TASK-160
  - **Temps estimé** : 2h
  - **Priorité** : 4
  - **Tech Stack** : TypeScript, Axios
  - **Critères d'acceptation** :
    - Npm package created
    - Type-safe methods
    - Documented examples
    - GitHub release

### 7.6 - Release & Go-Live

- [ ] **TASK-167** [P5] Configurer automated versioning (semantic-release)
  - **Description** : Automatic version bumps based on commits
  - **Dépendances** : TASK-002, TASK-148
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : semantic-release, GitHub
  - **Critères d'acceptation** :
    - Version bumping automated
    - Changelog generated
    - GitHub releases created
    - Docker tags versioned

- [ ] **TASK-168** [P5] Créer release checklist & runbook
  - **Description** : Pre-release verification, go-live checklist
  - **Dépendances** : TASK-164
  - **Temps estimé** : 1.5h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Markdown
  - **Critères d'acceptation** :
    - All tests passing
    - Documentation updated
    - Database migration tested
    - Rollback plan ready
    - Monitoring dashboards created

- [ ] **TASK-169** [P5] Effectuer staging deployment test run
  - **Description** : Dry-run complet en staging environment
  - **Dépendances** : TASK-147, TASK-151
  - **Temps estimé** : 3h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Kubernetes / Cloud Run
  - **Critères d'acceptation** :
    - All services deploy successfully
    - Database migrations work
    - Smoke tests pass
    - Rollback tested

- [ ] **TASK-170** [P5] Production deployment go-live
  - **Description** : Deploy to production, monitor, be ready to rollback
  - **Dépendances** : TASK-168, TASK-169
  - **Temps estimé** : 2h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Kubernetes / Cloud Run
  - **Critères d'acceptation** :
    - All services running
    - Health checks passing
    - Real-time monitoring
    - Incident team on-call
    - Rollback can be triggered

---

## 🔐 TÂCHES TRANSVERSALES (SÉCURITÉ & CHIFFREMENT)

- [ ] **TASK-171** Configurer encryption at rest pour tokens OAuth
  - **Description** : Rails `encrypts :access_token` pour DataStream
  - **Dépendances** : TASK-016, TASK-087
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : Rails encryption, ActiveRecord
  - **Critères d'acceptation** :
    - Tokens encrypted en DB
    - Transparent decryption
    - Key rotation documented

- [ ] **TASK-172** Configurer encryption in transit (TLS 1.3)
  - **Description** : All API endpoints HTTPS, TLS 1.3 minimum
  - **Dépendances** : TASK-154
  - **Temps estimé** : 1h
  - **Priorité** : 5 (Critique)
  - **Tech Stack** : NGINX, TLS 1.3
  - **Critères d'acceptation** :
    - TLS 1.3 configured
    - HSTS enabled (max-age=31536000)
    - SSL Labs A+ rating

- [ ] **TASK-173** Implémenter API rate limiting
  - **Description** : Rack-attack gem pour limit requests/user
  - **Dépendances** : TASK-011
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Rails, Rack-attack
  - **Critères d'acceptation** :
    - Rate limit 100 req/min per user
    - 1000 req/min per IP
    - Graceful 429 responses

- [ ] **TASK-174** Implémenter CSRF protection
  - **Description** : Rails CSRF tokens, SameSite cookies
  - **Dépendances** : TASK-011, TASK-020
  - **Temps estimé** : 1h
  - **Priorité** : 4
  - **Tech Stack** : Rails, Set-Cookie
  - **Critères d'acceptation** :
    - CSRF tokens validated
    - SameSite=Strict for sensitive cookies
    - No cookie leaks

- [ ] **TASK-175** Implémenter input validation & XSS prevention
  - **Description** : Sanitize inputs, output encoding, CSP headers
  - **Dépendances** : TASK-011, TASK-043
  - **Temps estimé** : 1.5h
  - **Priorité** : 4
  - **Tech Stack** : Rails, Content Security Policy
  - **Critères d'acceptation** :
    - All inputs validated
    - CSP headers set
    - XSS payloads blocked

---

## 📊 STATISTIQUES GLOBALES

| Métrique | Valeur |
|----------|--------|
| **Total Tâches** | 175 |
| **Tâches Critiques (P5)** | 98 |
| **Tâches Prioritaires (P4)** | 60 |
| **Tâches Standard (P3)** | 17 |
| **Heures estimées totales** | 480-520h |
| **Semaines à temps plein (40h/sem)** | 12-13 |
| **Phases** | 8 |

---

## 🎯 DÉPENDANCES CRITIQUES & ORDRE D'EXÉCUTION

```
PHASE 0 (Setup Infrastructure)
    ↓
PHASE 1 (Backend Rails)
    ↓
PHASE 2 (Frontend React) [peut commencer partiellement en parallèle avec Phase 1]
    ↓
PHASE 3 (ML Python) [peut commencer en parallèle avec Phase 1-2]
    ↓
PHASE 4 (Intégrations) [dépend de Phase 1-3]
    ↓
PHASE 5 (Agent Workflows) [dépend de Phase 1-4]
    ↓
PHASE 6 (Tests & Optimisation) [continu tout au long]
    ↓
PHASE 7 (Déploiement) [fin]
```

---

## 🚀 OPPORTUNITÉS DE PARALLÉLISATION

**Équipes simultanées possibles** :
1. **Backend Team** : PHASE 1 (Rails setup)
2. **Frontend Team** : PHASE 2 (React setup)
3. **ML Team** : PHASE 3 (Python setup)
4. **Integration Team** : PHASE 4 (après P1-P3)

**Parallélisation intra-phase** :
- Tâches du même service sans dépendances peuvent être parallélisées
- Exemple: DatabaseMigrations (TASK-014-018) peuvent démarrer en parallèle
- Services décorrélés (Rails vs React vs Python) peuvent être développés simultanément

---

## ✅ CRITÈRES DE SUCCÈS PAR PHASE

### PHASE 0 ✅
- [ ] Monorepo structure fonctionnelle
- [ ] CI/CD pipelines opérationels
- [ ] Docker & Local dev environment  
- [ ] PostgreSQL pgvector accessible

### PHASE 1 ✅
- [ ] Rails API expose tous endpoints
- [ ] Devise JWT auth fonctionne
- [ ] Solid Queue background jobs opérationels
- [ ] WebSocket Action Cable connecte

### PHASE 2 ✅
- [ ] React Dashboard affiche correctement
- [ ] Bento grid responsive
- [ ] OmniChat interactif
- [ ] Authentication flow complète

### PHASE 3 ✅
- [ ] FastAPI services répondent
- [ ] Email classification 80%+ accuracy
- [ ] Embeddings générés
- [ ] RAG search fonctionne

### PHASE 4 ✅
- [ ] OAuth Google/Microsoft/Plaid fonctionne
- [ ] Emails sync automatiquement
- [ ] Calendar events visibles
- [ ] Kijiji messages scraped

### PHASE 5 ✅
- [ ] Agent function calling fonctionne
- [ ] Voice commands transcrits
- [ ] Workflows exécutent complets
- [ ] Real-time notifications OK

### PHASE 6 ✅
- [ ] >80% test coverage
- [ ] Performance <100ms pour API
- [ ] No security vulnerabilities
- [ ] Monitoring dashboards actifs

### PHASE 7 ✅
- [ ] Production deployment successful
- [ ] Zero-downtime possible
- [ ] Monitoring en place
- [ ] Documentation complète

---

**Document généré** : 2026-07-19  
**Prochaine review** : Lors de la complétion de PHASE 0
