# Documentation Technique - PHASE 1: Backend Django

**Date**: 2026-07-22  
**Version**: 1.0  
**Statut**: ✅ COMPLÉTÉ

---

## 1. Résumé de la Phase

Cette phase a implémenté le backend Django complet avec API REST, authentification JWT, tâches asynchrones (Celery), et WebSockets temps réel.

---

## 2. Architecture Implémentée

### 2.1 Structure API

```
backend/
├── config/
│   ├── api.py              # Routeur principal Django Ninja
│   ├── urls.py             # URLs Django
│   ├── settings.py         # Configuration
│   ├── celery.py           # Configuration Celery
│   └── celery_schedule.py  # Planification tâches
├── apps/
│   ├── users/              # Auth + gestion utilisateurs
│   │   ├── api.py          # Endpoints: /register, /login, /me
│   │   ├── auth.py         # JWT Bearer authentication
│   │   ├── middleware.py    # Middleware JWT
│   │   ├── schemas.py      # Pydantic schemas
│   │   └── admin.py        # Configuration admin
│   ├── data_streams/       # Ingestion de données
│   │   ├── api.py          # CRUD + /process
│   │   ├── models.py       # DataStream model
│   │   └── schemas.py      # Pydantic schemas
│   ├── document_chunks/    # Mémoire RAG
│   │   ├── api.py          # CRUD + /search
│   │   ├── models.py       # DocumentChunk model
│   │   └── schemas.py      # Pydantic schemas
│   ├── alerts/             # Alertes agents
│   │   ├── api.py          # CRUD + /acknowledge, /execute, /dismiss
│   │   ├── models.py       # AgentAlert model
│   │   ├── consumers.py    # WebSocket consumers
│   │   └── schemas.py      # Pydantic schemas
│   └── agents/             # Orchestration CrewAI
│       ├── api.py          # /chat, /status, /voice
│       ├── tasks.py        # Celery tasks
│       ├── routing.py      # WebSocket routing
│       └── schemas.py      # Pydantic schemas
```

### 2.2 Endpoints API

#### Authentication (auth=None)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/users/register` | Inscription utilisateur |
| POST | `/api/users/login` | Connexion |
| POST | `/api/users/refresh` | Rafraîchir token |

#### Users (auth=JWT)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/users/me` | Profil utilisateur |
| PUT | `/api/users/me` | Mettre à jour profil |
| GET | `/api/users/` | Liste utilisateurs (admin) |
| GET | `/api/users/{id}` | Détail utilisateur (admin) |

#### Data Streams (auth=JWT)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/data-streams/` | Créer flux de données |
| GET | `/api/data-streams/` | Lister flux (pagination) |
| GET | `/api/data-streams/{id}` | Détail flux |
| DELETE | `/api/data-streams/{id}` | Supprimer flux |
| POST | `/api/data-streams/{id}/process` | Traiter flux |

#### Document Chunks (auth=JWT)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/document-chunks/` | Lister chunks |
| GET | `/api/document-chunks/{id}` | Détail chunk |
| POST | `/api/document-chunks/search` | Recherche sémantique |
| DELETE | `/api/document-chunks/{id}` | Supprimer chunk |

#### Alerts (auth=JWT)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/alerts/` | Lister alertes |
| GET | `/api/alerts/stats` | Statistiques alertes |
| GET | `/api/alerts/{id}` | Détail alerte |
| PUT | `/api/alerts/{id}` | Mettre à jour alerte |
| POST | `/api/alerts/{id}/acknowledge` | Accuser réception |
| POST | `/api/alerts/{id}/execute` | Exécuter action |
| POST | `/api/alerts/{id}/dismiss` | Ignorer alerte |

#### Agents (auth=JWT)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/agents/chat` | Envoyer message agent |
| GET | `/api/agents/status` | Statut agents |
| POST | `/api/agents/voice` | Commande vocale |

### 2.3 WebSocket Endpoints

| Endpoint | Consumer | Description |
|----------|----------|-------------|
| `ws://localhost:8000/ws/alerts/` | AlertsConsumer | Alertes temps réel |
| `ws://localhost:8000/ws/analytics/` | AnalyticsConsumer | Analytics temps réel |
| `ws://localhost:8000/ws/notifications/` | NotificationsConsumer | Notifications temps réel |

### 2.4 Celery Tasks

| Task | Description | Fréquence |
|------|-------------|-----------|
| `process_data_stream` | Traiter flux de données | On-demand |
| `generate_embeddings` | Générer embeddings | On-demand |
| `execute_agent_action` | Exécuter action agent | On-demand |
| `sync_gmail` | Synchroniser Gmail | Toutes les heures |
| `sync_plaid` | Synchroniser Plaid | Toutes les 4 heures |

---

## 3. Modèles de Données

### 3.1 User (apps/users/models.py)

```python
class User(AbstractUser):
    id = UUIDField(primary_key=True)
    email = EmailField(unique=True)
    phone_number = CharField(blank=True)
    avatar_url = URLField(blank=True)
    google_access_token = TextField(encrypted)
    google_refresh_token = TextField(encrypted)
    plaid_access_token = TextField(encrypted)
    email_notifications = BooleanField(default=True)
    push_notifications = BooleanField(default=True)
    webhook_url = URLField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 3.2 DataStream (apps/data_streams/models.py)

```python
class DataStream(Model):
    id = UUIDField(primary_key=True)
    user = ForeignKey(User)
    source_type = CharField(choices=[gmail, kijiji, plaid, google_calendar, manual])
    payload = JSONField()
    raw_data = JSONField(blank=True)
    processed_at = DateTimeField(blank=True)
    status = CharField(choices=[pending, processing, completed, failed])
    error_message = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 3.3 DocumentChunk (apps/document_chunks/models.py)

```python
class DocumentChunk(Model):
    id = UUIDField(primary_key=True)
    stream = ForeignKey(DataStream)
    content = TextField()
    embedding = JSONField()  # 384 dimensions
    cluster_category = CharField(choices=[recrutement, urgent, finance, kijiji_deal, calendar, general])
    metadata = JSONField(blank=True)
    chunk_index = IntegerField(default=0)
    total_chunks = IntegerField(default=1)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 3.4 AgentAlert (apps/alerts/models.py)

```python
class AgentAlert(Model):
    id = UUIDField(primary_key=True)
    user = ForeignKey(User)
    title = CharField(max_length=255)
    description = TextField()
    severity = CharField(choices=[low, medium, high, critical])
    status = CharField(choices=[pending, acknowledged, executed, dismissed])
    action_payload = JSONField(blank=True)
    source_type = CharField(blank=True)
    source_id = UUIDField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
    acknowledged_at = DateTimeField(blank=True)
    executed_at = DateTimeField(blank=True)
```

---

## 4. Fonctionnalités Implémentées

### 4.1 Authentification JWT

- Inscription avec validation email unique
- Connexion avec email/password
- Token refresh automatique
- Middleware JWT pour routes protégées
- Blacklist des tokens révoqués

### 4.2 API REST (Django Ninja)

- Routes typées avec Pydantic schemas
- Pagination automatique
- Filtrage par paramètres
- Documentation OpenAPI auto-générée
- Auth optionnelle par route

### 4.3 WebSockets (Django Channels)

- Consumers asynchrones pour temps réel
- Groupes par utilisateur
- Support alerts, analytics, notifications
- Authentification WebSocket

### 4.4 Tâches Asynchrones (Celery)

- Workers pour traitement parallèle
- Beat scheduler pour tâches périodiques
- Retry automatique avec backoff
- Monitoring via Redis

---

## 5. Commandes Utiles

### Démarrage

```bash
# Démarrer les services
docker compose up -d

# Exécuter les migrations
docker compose exec backend python manage.py migrate

# Créer un superutilisateur
docker compose exec backend python manage.py createsuperuser

# Accéder à l'API docs
open http://localhost:8000/api/docs
```

### Développement

```bash
# Shell Django
docker compose exec backend python manage.py shell

# Créer un token test
docker compose exec backend python manage.py shell -c "
from apps.users.models import User
from rest_framework_simplejwt.tokens import RefreshToken
user = User.objects.first()
tokens = RefreshToken.for_user(user)
print(f'Access: {tokens.access_token}')
"

# Tester un endpoint
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'
```

### Celery

```bash
# Voir les tâches en cours
docker compose exec celery_worker celery -A config inspect active

# Voir les tâches planifiées
docker compose exec celery_beat celery -A config inspect scheduled
```

---

## 6. Prochaines Étapes

### PHASE 1 (suite) : Authorization & Controllers

1. **TASK-022**: Implémenter authorization policies
2. **TASK-023-026**: Créer controllers CRUD complets
3. **TASK-027**: Créer serializers JSON

### PHASE 1 : External Services

4. **TASK-028-032**: Créer clients OAuth (Google, Plaid)
5. **TASK-033-036**: Créer background jobs
6. **TASK-037-039**: Configurer WebSockets

---

## 7. Notes Techniques

### Sécurité

- Tokens JWT avec expiration configurable
- Password hashing avec PBKDF2
- CORS restreint aux origines autorisées
- Rate limiting configuré

### Performance

- Pagination pour toutes les listes
- Requêtes optimisées avec select_related
- Cache Redis pour sessions
- Workers Celery parallèles

### Monitoring

- Logging structuré avec timestamps
- Health checks Docker
- Métriques Celery
- Sentry pour error tracking

---

**Document créé**: 2026-07-22  
**Prochaine mise à jour**: PHASE 1 suite (Authorization & Controllers)
