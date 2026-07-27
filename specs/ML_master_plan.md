# PLAN DE DÉVELOPPEMENT DÉTAILLÉ - ML (2026)

**Statut** : EN COURS DE DÉVELOPPEMENT  
**Date de création** : 2026-07-19  
**Durée estimée totale** : ~480-520 heures (12-13 semaines à temps plein)

---

## 📊 RÉSUMÉ EXÉCUTIF

### Phases de Développement
- **PHASE 0** : Initialisation & Infrastructure (40-50h)
- **PHASE 1** : Backend Django (120-140h)
- **PHASE 2** : Frontend React 19 (100-120h)
- **PHASE 3** : ML Python & Clustering (80-100h)
- **PHASE 4** : Intégrations Externes (60-80h)
- **PHASE 5** : Features Agents & Workflows (50-60h)
- **PHASE 6** : Tests & Optimisation (30-40h)
- **PHASE 7** : Déploiement & Documentation (20-30h)

### Tâches Transversales
- Sécurité & Chiffrement (15-20h)
- Monitoring & Logging (15-20h)

**Total estimé : 175 tâches réparties sur 8 phases**

---

## 📋 CONTENU COMPLET

[Archivé depuis: .specify/tasks.md généré par Spec Kit - 2026-07-19]

### PHASE 0 : INITIALISATION & INFRASTRUCTURE (T001-T010)

#### 0.1 - Setup Monorepo & Repositories

- **TASK-001** [P5] Créer la structure monorepo avec yarn workspaces
- **TASK-002** [P5] Initialiser le repository Git avec CI/CD (GitHub Actions)
- **TASK-003** [P5] Configurer Docker & Docker Compose pour dev local
- **TASK-004** [P5] Configurer PostgreSQL 16 avec extension pgvector

#### 0.2 - Configuration Environnement

- **TASK-005** [P5] Configurer variables d'environnement (.env, .env.local)
- **TASK-006** [P5] Configurer secrets management (Django settings, .env)

#### 0.3 - Tooling & Development Setup

- **TASK-007** [P4] Configurer ESLint + Prettier pour React/Next.js
- **TASK-008** [P4] Configurer Black + isort pour Django
- **TASK-009** [P4] Configurer Pytest + Black pour Python ML
- **TASK-010** [P4] Configurer Husky + Pre-commit hooks

### PHASE 1 : BACKEND DJANGO (T011-T042)

#### 1.1 - Initialisation Django API

- **TASK-011** [P5] Créer nouveau projet Django avec Django Ninja
- **TASK-012** [P5] Configurer Celery pour tâches asynchrones
- **TASK-013** [P5] Configurer Django Channels pour WebSockets temps réel

#### 1.2 - Database Schema & Models

- **TASK-014** [P5] Créer migration users & base schema
- **TASK-015** [P5] Créer User model avec associations
- **TASK-016** [P5] Créer migration data_streams & modèle
- **TASK-017** [P5] Créer migration document_chunks & indexes HNSW
- **TASK-018** [P5] Créer migration agent_alerts & modèle
- **TASK-019** [P5] Créer models pour associations & scopes

#### 1.3 - Authentication & Authorization

- **TASK-020** [P5] Configurer Django authentication avec JWT tokens
- **TASK-021** [P5] Configurer Django settings pour JWT secret
- **TASK-022** [P4] Implémenter authorization policies

#### 1.4 - Core API Controllers & Serializers

- **TASK-023** [P5] Créer UsersController (CRUD)
- **TASK-024** [P5] Créer DataStreamsController (ingestion)
- **TASK-025** [P5] Créer DocumentChunksController (RAG search)
- **TASK-026** [P5] Créer AlertsController (CRUD + actions)
- **TASK-027** [P4] Créer serializers JSON

#### 1.5 - External Service Integration Layer

- **TASK-028** [P4] Créer base class pour OAuth clients (Google, Microsoft)
- **TASK-029** [P4] Créer GmailClient service
- **TASK-030** [P4] Créer CalendarClient service
- **TASK-031** [P4] Créer PlaidClient service
- **TASK-032** [P4] Créer KijijiScraperService (Playwright)

#### 1.6 - Background Jobs & Workers

- **TASK-033** [P5] Créer EmailAnalysisJob (enqueue au POST /data_streams)
- **TASK-034** [P5] Créer EmbeddingGenerationJob
- **TASK-035** [P5] Créer AgentExecutionJob (run function calls)
- **TASK-036** [P4] Créer KijijiScraperJob (recurring)

#### 1.7 - WebSockets & Real-time Features

- **TASK-037** [P5] Créer AlertsChannel (WebSocket real-time)
- **TASK-038** [P4] Créer AnalyticsChannel
- **TASK-039** [P4] Créer NotificationsChannel

#### 1.8 - Error Handling & Logging

- **TASK-040** [P4] Configurer Sentry pour error tracking
- **TASK-041** [P4] Configurer Django logging & log rotation
- **TASK-042** [P4] Créer middleware pour API error responses

### PHASE 2 : FRONTEND REACT 19 (T043-T069)

#### 2.1 - Next.js App Setup

- **TASK-043** [P5] Créer app Next.js 14+ avec App Router
- **TASK-044** [P5] Configurer TypeScript strictement
- **TASK-045** [P5] Configurer TanStack Query
- **TASK-046** [P5] Configurer Zustand pour state management

#### 2.2 - Authentication & Routing

- **TASK-047** [P5] Créer AuthContext et hooks useAuth
- **TASK-048** [P5] Créer route protégée /dashboard
- **TASK-049** [P5] Créer pages d'authentification (/login, /signup)
- **TASK-050** [P4] Créer route /settings (profil utilisateur)

#### 2.3 - UI Components & Design System

- **TASK-051** [P5] Configurer Shadcn/ui components
- **TASK-052** [P4] Créer component Button primaire/secondaire
- **TASK-053** [P4] Créer component Card réutilisable
- **TASK-054** [P4] Créer component Alert/Toast
- **TASK-055** [P4] Créer component Form avec validation
- **TASK-056** [P4] Créer component Modal/Dialog

#### 2.4 - Dashboard Layout (Bento Grid)

- **TASK-057** [P5] Créer layout principal du dashboard
- **TASK-058** [P5] Créer component OmniChat (bloc central)
- **TASK-059** [P5] Créer component AlertHub (bloc alertes)
- **TASK-060** [P5] Créer component FinancialAnalytics (bloc patrimoine)
- **TASK-061** [P5] Créer component ActivityMap (bloc services)

#### 2.5 - Advanced UI Features

- **TASK-062** [P4] Implémenter dark mode (Tailwind CSS)
- **TASK-063** [P4] Implémenter responsive design mobile-first
- **TASK-064** [P4] Implémenter animations & transitions
- **TASK-065** [P4] Configurer PWA manifest (offline support optionnel)

#### 2.6 - WebSocket & Real-time Integration

- **TASK-066** [P5] Créer WebSocket client pour Django Channels
- **TASK-067** [P5] Implémenter hook useRealtimeAlerts
- **TASK-068** [P4] Implémenter hook useRealtimeAnalytics
- **TASK-069** [P4] Implémenter hook useRealtimeNotifications

### PHASE 3 : MACHINE LEARNING & CLUSTERING (T070-T086)

#### 3.1 - CrewAI Microservice Infrastructure

- **TASK-070** [P5] Créer structure microservice CrewAI avec FastAPI
- **TASK-071** [P5] Configurer connexion PostgreSQL depuis Python
- **TASK-072** [P5] Créer service NIM (NVIDIA Inference Microservices)
- **TASK-073** [P4] Créer service d'embeddings

#### 3.2 - Email Clustering & Classification

- **TASK-074** [P5] Créer classifier pour emails (recrutement/urgent/finance)
- **TASK-075** [P5] Créer entity extractor pour emails (sender, date, objet)
- **TASK-076** [P5] Créer endpoint POST /analyze_email
- **TASK-077** [P4] Créer endpoint POST /chunk_email (RAG)

#### 3.3 - Anomaly Detection (Isolation Forest)

- **TASK-078** [P5] Créer model Isolation Forest pour transactions
- **TASK-079** [P5] Créer endpoint POST /detect_anomalies
- **TASK-080** [P4] Créer matrix Pearson correlations pour financials
- **TASK-081** [P4] Créer endpoint POST /financial_insights

#### 3.4 - Kijiji Message Analysis

- **TASK-082** [P4] Créer classifier pour Kijiji messages
- **TASK-083** [P4] Créer endpoint POST /analyze_kijiji_message

#### 3.5 - Vector Search & RAG

- **TASK-084** [P5] Créer endpoint POST /search_documents
- **TASK-085** [P5] Créer endpoint POST /rag_context
- **TASK-086** [P4] Créer batch embedding job

### PHASE 4 : INTÉGRATIONS EXTERNES (T087-T105)

#### 4.1 - Gmail Integration

- **TASK-087** [P5] Configurer Google OAuth flow
- **TASK-088** [P5] Créer GmailSyncJob pour sync emails
- **TASK-089** [P5] Créer service pour send email replies
- **TASK-090** [P4] Créer endpoint React pour trigger sync Gmail

#### 4.2 - Google Calendar Integration

- **TASK-091** [P5] Configurer Google Calendar API permissions
- **TASK-092** [P5] Créer CalendarSyncJob
- **TASK-093** [P5] Créer service create_calendar_event
- **TASK-094** [P4] Créer service Teams meeting creation
- **TASK-095** [P4] Créer calendrier widget React

#### 4.3 - Plaid Integration

- **TASK-096** [P5] Configurer Plaid Link flow
- **TASK-097** [P5] Créer PlaidLinkController
- **TASK-098** [P5] Créer PlaidSyncJob
- **TASK-099** [P5] Créer AccountsController
- **TASK-100** [P4] Créer React component Plaid Link modal
- **TASK-101** [P4] Créer React component Accounts listing

#### 4.4 - Kijiji Scraping

- **TASK-102** [P5] Créer Python script Kijiji scraper
- **TASK-103** [P5] Créer endpoint Django pour webhook Kijiji scraper
- **TASK-104** [P5] Créer KijijiScraperJob (recurring)
- **TASK-105** [P4] Créer React component Kijiji messages view

### PHASE 5 : FEATURES AGENTS & WORKFLOWS (T106-T120)

#### 5.1 - Agent CrewAI Integration

- **TASK-106** [P5] Implémenter CrewAI agents orchestration
- **TASK-107** [P5] Créer AgentCommandService (CrewAI + NIM)
- **TASK-108** [P5] Créer ToolExecutor (exécute les function calls)
- **TASK-109** [P5] Créer MessagesController pour chat API
- **TASK-110** [P5] Créer AgentExecutionJob (streaming responses)

#### 5.2 - Voice Command Integration

- **TASK-111** [P5] Intégrer Whisper API pour speech-to-text
- **TASK-112** [P5] Créer Web Audio API recording (React)
- **TASK-113** [P4] Créer voice response (text-to-speech)

#### 5.3 - Smart Workflows

- **TASK-114** [P5] Créer workflow "Confirm RDV" (booking confirmation)
- **TASK-115** [P5] Créer workflow "Financial Anomaly Alert"
- **TASK-116** [P4] Créer workflow "Email Auto-Reply"
- **TASK-117** [P4] Créer workflow "Kijiji Negotiation"

#### 5.4 - Notification & Alert Management

- **TASK-118** [P5] Créer notification preferences UI
- **TASK-119** [P5] Créer alert severity + priority rules
- **TASK-120** [P4] Créer email notification sending

### PHASE 6 : TESTS & OPTIMISATION (T121-T144)

#### 6.1 - Backend Testing

- **TASK-121** [P5] Configurer Pytest pour Django
- **TASK-122** [P5] Écrire unit tests pour Models
- **TASK-123** [P5] Écrire request specs pour API endpoints
- **TASK-124** [P4] Écrire integration tests pour Jobs
- **TASK-125** [P4] Écrire service specs pour OAuth/external APIs
- **TASK-126** [P4] Configurer coverage reporting

#### 6.2 - Frontend Testing

- **TASK-127** [P5] Configurer Vitest + React Testing Library
- **TASK-128** [P5] Écrire component tests
- **TASK-129** [P5] Écrire hook tests
- **TASK-130** [P4] Configurer Playwright pour E2E tests
- **TASK-131** [P4] Écrire E2E tests pour critical flows
- **TASK-132** [P4] Configurer Percy/Chromatic visual regression

#### 6.3 - Python ML Testing

- **TASK-133** [P4] Écrire Pytest tests pour ML services
- **TASK-134** [P4] Créer fixtures de test données

#### 6.4 - Performance Optimization

- **TASK-135** [P5] Optimiser database queries
- **TASK-136** [P5] Configurer Redis caching
- **TASK-137** [P5] Implémenter API response caching
- **TASK-138** [P4] Optimiser React bundle size
- **TASK-139** [P4] Optimiser image assets
- **TASK-140** [P4] Configurer CDN pour static assets

#### 6.5 - Security & Penetration Testing

- **TASK-141** [P5] Configurer Django security checks
- **TASK-142** [P5] Audit JWT token security
- **TASK-143** [P4] Test CORS configuration
- **TASK-144** [P4] Test OAuth token refresh security

### PHASE 7 : DÉPLOIEMENT & DOCUMENTATION (T145-T170)

#### 7.1 - Deployment Infrastructure

- **TASK-145** [P5] Configurer Dockerfile production
- **TASK-146** [P5] Configurer docker-compose production
- **TASK-147** [P5] Configurer Kubernetes deployment
- **TASK-148** [P5] Configurer CI/CD pipeline (GitHub Actions)
- **TASK-149** [P5] Configurer monitoring & alerting (Prometheus + Grafana)
- **TASK-150** [P5] Configurer log centralization (Loki)

#### 7.2 - Production Database & Migration

- **TASK-151** [P5] Configurer PostgreSQL production
- **TASK-152** [P5] Créer migration strategy (zero-downtime)
- **TASK-153** [P4] Configurer database seeding

#### 7.3 - Secrets & SSL/TLS Management

- **TASK-154** [P5] Configurer SSL/TLS certificates (Let's Encrypt)
- **TASK-155** [P5] Configurer secrets management
- **TASK-156** [P5] Implémenter database encryption at rest

#### 7.4 - Monitoring & Incident Response

- **TASK-157** [P5] Configurer alerting (PagerDuty intégration)
- **TASK-158** [P5] Créer runbook incidents
- **TASK-159** [P4] Configurer APM

#### 7.5 - Documentation

- **TASK-160** [P5] Écrire API documentation (OpenAPI/Swagger)
- **TASK-161** [P5] Écrire README.md project overview
- **TASK-162** [P5] Écrire Architecture.md documentation
- **TASK-163** [P5] Écrire Developer Guide
- **TASK-164** [P5] Écrire Deployment Guide
- **TASK-165** [P5] Écrire Operations Guide
- **TASK-166** [P4] Créer API client library (SDK optionnel)

#### 7.6 - Release & Go-Live

- **TASK-167** [P5] Configurer automated versioning
- **TASK-168** [P5] Créer release checklist & runbook
- **TASK-169** [P5] Effectuer staging deployment test run
- **TASK-170** [P5] Production deployment go-live

### TÂCHES TRANSVERSALES (T171-T175)

- **TASK-171** Configurer encryption at rest pour tokens OAuth
- **TASK-172** Configurer encryption in transit (TLS 1.3)
- **TASK-173** Implémenter API rate limiting
- **TASK-174** Implémenter CSRF protection
- **TASK-175** Implémenter input validation & XSS prevention

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

## 🎯 ORDRE D'EXÉCUTION RECOMMANDÉ

```
PHASE 0 (Setup Infrastructure)
    ↓
PHASE 1 (Backend Django)
    ↓ [Parallèle possible]
PHASE 2 (Frontend React) & PHASE 3 (ML Python CrewAI)
    ↓
PHASE 4 (Intégrations)
    ↓
PHASE 5 (Agent Workflows)
    ↓
PHASE 6 (Tests & Optimisation) [Continu tout au long]
    ↓
PHASE 7 (Déploiement)
```

**Archive créée** : 2026-07-19
**Contenu** : 2220 lignes (175 tâches détaillées avec critères d'acceptation)
