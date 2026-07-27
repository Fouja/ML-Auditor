# ARCHITECTURE TECHNIQUE - ML (2026)
## Agent Omniscient Autonome via Django + CrewAI + NVIDIA NIM

---

## 🎯 OBJECTIF
Agent autonome centralisé ingérant emails, calendriers, données bancaires, messages Kijiji. Classification IA (clustering, anomalies), exécution d'actions via Function Calling.

---

## 🏗️ ARCHITECTURE UNIFIÉE

### **Backend: Django (Python 3.13) API asynchrone**
- **Framework**: Django Ninja (Pydantic, async/await)
- **Agents IA**: CrewAI orchestrant 3 agents
  1. **Agent Tri d'Emails** : Clustering (recrutement/urgent/finance)
  2. **Agent Audit Financier** : Anomalies (Isolation Forest)
  3. **Agent Scraper Kijiji** : Négociation & pricing
- **LLM**: NVIDIA NIM (OpenAI-compatible) – Llama 3.3 / DeepSeek V3
- **Vectoriel**: pgvector dans PostgreSQL (HNSW indexing)
- **Tasks**: Celery pour jobs async
- **WebSockets**: Django Channels (real-time alerts/analytics)

### **Base de Données: PostgreSQL 16 + pgvector**
```sql
-- Unification données relationnelles + vectorielles
-- Tables: users, data_streams, document_chunks (embeddings), agent_alerts
-- HNSW index sur document_chunks.embedding pour RAG similarity search
```

### **Frontends Multi-plateformes (React 19)**
| Plateforme | Tech | Usage |
|-----------|------|-------|
| Desktop | Electron + React 19 + Tailwind v4 | App lourde, privée (style Obsidian) |
| Mobile | React Native (Expo) | Audio natif, notifications push |

---

## 📊 SCHÉMA POSTGRESQL

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Data Streams (Emails, Kijiji, Plaid, Calendar)
CREATE TABLE data_streams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'gmail', 'kijiji', 'plaid', 'google_calendar'
    payload JSONB NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- RAG Memory (Mémoire sémantique)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID REFERENCES data_streams(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(384), -- NVIDIA NIM embeddings
    cluster_category VARCHAR(100), -- 'recrutement', 'urgent', 'finance', 'kijiji_deal'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Agent Alerts & Actions
CREATE TABLE agent_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL, -- 'low', 'medium', 'critical'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'acknowledged', 'executed'
    action_payload JSONB, -- Function calling args
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔄 WORKFLOWS (3 AGENTS CREWAI)

### **Agent 1: Email Clustering**
1. Flask POST /data_streams reçoit email brut
2. CrewAI agent + NIM classifie (recrutement/urgent/finance)
3. Entity extraction: sender, dates, montants
4. DocumentChunk créé avec embedding
5. AgentAlert si prioritaire

### **Agent 2: Audit Financier**
1. Transactions Plaid → data_streams
2. Isolation Forest détecte anomalies
3. Pearson correlations → doublons abonnements
4. AlertHub affiche recommandations

### **Agent 3: Kijiji Negotiation**
1. Playwright script → messages Kijiji
2. CrewAI analyse + classifie (spam/genuine/lowball)
3. Suggestion de contre-offre
4. Brouillon réponse prêt

---

## 🎨 UI - REACT BENTO GRID (Desktop/Mobile)

**Dashboard 4-bloc:**
1. **OmniChat** (centre) : Text + voice (Whisper) → CrewAI execution
2. **AlertHub** (vertical) : Alertes triées par criticité
3. **FinancialAnalytics** (chart) : Solde + anomalies
4. **ActivityMap** (status) : Gmail, Calendar, Kijiji, Plaid sync

---

## 🔐 SÉCURITÉ

- OAuth2 tokens chiffrés en DB (Django `encrypted_model_fields`)
- HTTPS/TLS 1.3 obligatoire
- JWT tokens + refresh logic
- Isolation des données utilisateur
- Microservice Python local (pas transit réseau sensible)

---

## 📦 DÉPENDANCES CLÉS

### Backend
```
django==4.2
djangorestframework==3.14
django-ninja==1.3
django-channels==4.1
celery==5.4
psycopg[binary]==3.1
sqlalchemy==2.0
crewai==0.1
openai==1.3
scikit-learn==1.4
pandas==2.1
pgvector==0.2
```

### Frontend
```
react==19
next==14
tailwindcss==4
react-hook-form
zustand
tanstack/react-query
shadcn/ui
```

---

## ⚡ ITÉRATION 1 (MVP)

**Scope**: Infrastructure + Auth + Basic RAG

1. **Django + PostgreSQL + pgvector** setup
2. **User Auth** (JWT)
3. **Email ingestion** (Gmail OAuth)
4. **Basic clustering** (NIM LLM)
5. **Frontend skeleton** (Auth + Dashboard layout)

---

**Date Création**: 2026-07-19  
**Statut**: ARCHITECTURE PIVOT DJANGO ✅
