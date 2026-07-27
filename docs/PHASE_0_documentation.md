# Documentation Technique - PHASE 0: Initialisation & Infrastructure

**Date**: 2026-07-22  
**Version**: 1.0  
**Statut**: ✅ COMPLÉTÉ

---

## 1. Résumé de la Phase

Cette phase a établi l'infrastructure de base du projet ML-Auditor, incluant la structure monorepo, la configuration Docker, les bases de données, et les outils de développement.

---

## 2. Architecture Créée

### 2.1 Structure Monorepo

```
ml-auditor/
├── backend/                    # Django API (Python 3.13)
│   ├── config/                 # Configuration Django
│   │   ├── settings.py         # Paramètres principaux
│   │   ├── urls.py             # URLs principaux
│   │   ├── wsgi.py             # WSGI entry point
│   │   ├── asgi.py             # ASGI entry point
│   │   └── celery.py           # Configuration Celery
│   ├── apps/                   # Applications Django
│   │   ├── users/              # Gestion des utilisateurs
│   │   ├── data_streams/       # Ingestion de données
│   │   ├── document_chunks/    # Mémoire RAG
│   │   ├── alerts/             # Alertes agents
│   │   └── agents/             # Orchestration CrewAI
│   ├── static/                 # Fichiers statiques
│   ├── media/                  # Fichiers media
│   ├── templates/              # Templates Django
│   └── requirements.txt        # Dépendances Python
├── frontend/                   # React 19 + Next.js
├── ml-service/                 # Microservice CrewAI
├── docker/                     # Configurations Docker
│   ├── Dockerfile.backend      # Image backend
│   └── init.sql                # Initialisation PostgreSQL
├── .github/workflows/          # CI/CD GitHub Actions
├── docker-compose.yml          # Orchestration Docker
├── .env                        # Variables d'environnement
├── .env.example                # Template variables
├── .gitignore                  # Fichiers ignorés
├── package.json                # Configuration yarn workspaces
└── README.md                   # Documentation projet
```

### 2.2 Services Docker

| Service | Port | Description |
|---------|------|-------------|
| `db` | 5432 | PostgreSQL 16 + pgvector |
| `redis` | 6379 | Cache, Celery, Channels |
| `backend` | 8000 | Django API |
| `celery_worker` | - | Tâches asynchrones |
| `celery_beat` | - | Planificateur tâches |
| `frontend` | 3000 | React/Next.js |

---

## 3. Fichiers Créés

### 3.1 Configuration Django

**`backend/config/settings.py`**
- Configuration modulaire avec `django-environ`
- Support multi-environnements (dev/prod)
- Intégration Sentry pour monitoring
- Configuration JWT pour authentification
- Support Redis pour cache et WebSockets

**`backend/config/celery.py`**
- Configuration Celery avec autodiscover
- Support tâches asynchrones

**`backend/config/asgi.py`**
- Support HTTP et WebSocket via Channels
- Middleware d'authentification WebSocket

### 3.2 Modèles de Données

**`apps/users/models.py`**
- Modèle User personnalisé avec UUID
- Tokens OAuth chiffrés (Google, Plaid)
- Préférences de notification

**`apps/data_streams/models.py`**
- Modèle DataStream pour ingestion
- Support 5 sources: gmail, kijiji, plaid, google_calendar, manual
- Statuts de traitement: pending, processing, completed, failed

**`apps/document_chunks/models.py`**
- Modèle DocumentChunk pour RAG
- Embeddings vectoriels (384 dimensions)
- Catégories de clustering

**`apps/alerts/models.py`**
- Modèle AgentAlert pour notifications
- Niveaux de sévérité: low, medium, high, critical
- Actions automatiques via function calling

### 3.3 Docker

**`docker/Dockerfile.backend`**
- Multi-stage build pour optimisation
- Utilisateur non-root pour sécurité
- Health check intégré
- Gunicorn avec Uvicorn worker

**`docker-compose.yml`**
- Services avec health checks
- Volumes persistants
- Dépendances configurées

### 3.4 CI/CD

**`.github/workflows/ci.yml`**
- Tests backend avec PostgreSQL et Redis
- Tests frontend
- Build Docker
- Code coverage avec Codecov

---

## 4. Dépendances Installées

### Backend (Python)

| Package | Version | Usage |
|---------|---------|-------|
| django | 4.2.17 | Framework web |
| django-ninja | 1.3.0 | API REST |
| celery | 5.4.0 | Tâches asynchrones |
| django-channels | 4.2.0 | WebSockets |
| psycopg | 3.2.3 | PostgreSQL |
| pgvector | 0.3.6 | Vector search |
| crewai | 0.100.1 | Orchestration IA |
| openai | 1.57.4 | Client NIM |
| black | 24.10.0 | Formatage code |
| pytest | 8.3.4 | Tests |

### Infrastructure

| Outil | Version | Usage |
|-------|---------|-------|
| PostgreSQL | 16 | Base de données |
| pgvector | 0.3 | Extensions vectorielles |
| Redis | 7 | Cache et messaging |
| Docker | latest | Conteneurisation |

---

## 5. Commandes Utiles

### Démarrage

```bash
# Copier les variables d'environnement
cp .env.example .env

# Démarrer l'environnement de développement
docker compose up -d

# Exécuter les migrations
docker compose exec backend python manage.py migrate

# Créer un superutilisateur
docker compose exec backend python manage.py createsuperuser
```

### Développement

```bash
# Logs en temps réel
docker compose logs -f backend

# Shell Django
docker compose exec backend python manage.py shell

# Tests
cd backend && pytest

# Formatage code
cd backend && black . && isort .
```

### Maintenance

```bash
# Arrêter tous les services
docker compose down

# Supprimer les volumes
docker compose down -v

# Reconstruire les images
docker compose build --no-cache
```

---

## 6. Prochaines Étapes

### PHASE 1: Backend Django (T011-T042)

1. **TASK-011**: Créer nouveau projet Django avec Django Ninja
2. **TASK-012**: Configurer Celery pour tâches asynchrones
3. **TASK-013**: Configurer Django Channels pour WebSockets

---

## 7. Notes Techniques

### Sécurité

- Tokens OAuth chiffrés via `django-encrypted-model-fields`
- JWT avec rotation des tokens
- HTTPS/TLS obligatoire en production
- CORS configuré pour le développement

### Performance

- PostgreSQL avec index HNSW pour recherche vectorielle
- Redis pour cache et sessions
- Celery pour traitement asynchrone
- Gunicorn avec Uvicorn worker

### Monitoring

- Sentry intégré pour error tracking
- Logging structuré avec rotation
- Health checks Docker
- Métriques Prometheus (optionnel)

---

**Document créé**: 2026-07-22  
**Prochaine mise à jour**: PHASE 1 Backend Django
