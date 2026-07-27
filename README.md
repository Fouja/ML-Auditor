# ML-Auditor

Autonomous AI agent system for intelligent management of emails, calendars, banking data, and Kijiji marketplace messages.

## Architecture

```
ml-auditor/
├── backend/              # Django 4.2 + Django Ninja API
│   ├── apps/
│   │   ├── users/        # Auth, JWT, OAuth clients
│   │   ├── workspace/    # Tasks, Calendar, News feeds, Widgets
│   │   ├── agents/       # AI agent orchestration, tools, workflows
│   │   ├── integrations/ # Email/Calendar/Plaid/Canva/Kijiji sync
│   │   ├── alerts/       # Alert system
│   │   ├── data_streams/ # Data pipeline
│   │   └── document_chunks/ # RAG embeddings (pgvector)
│   ├── config/           # Django settings, URLs, Celery
│   ├── tests/            # 38 passing tests
│   └── manage.py
├── frontend/             # Next.js 14 + React 19
│   ├── src/
│   │   ├── app/          # App Router pages
│   │   ├── components/   # UI components + dashboard widgets
│   │   ├── stores/       # Zustand state management
│   │   ├── lib/          # API client, utils
│   │   ├── hooks/        # Custom React hooks
│   │   └── __tests__/    # 13 passing tests
│   └── package.json
├── ml-service/           # FastAPI + CrewAI + NVIDIA NIM
│   ├── services/         # Classifier, embeddings, anomaly detection
│   └── main.py
├── sdk/                  # Python client library
├── deployment/           # K8s, Nginx, Prometheus, Grafana, Loki
├── docker/               # Dockerfiles (backend, frontend, ML)
├── scripts/              # Migration, seeding, SSL setup
├── docs/                 # Phase documentation
└── specs/                # Master plan, architecture specs
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 4.2 + Django Ninja + Celery + Channels |
| **Frontend** | Next.js 14 + React 19 + Tailwind CSS + TanStack Query + Zustand |
| **ML Service** | FastAPI + CrewAI (optional) + NVIDIA NIM (Llama 3.3 / DeepSeek V3) |
| **Database** | PostgreSQL 16 + pgvector + Redis |
| **Infrastructure** | Docker Compose + Kubernetes + Nginx |
| **Monitoring** | Prometheus + Grafana + Loki + Sentry |
| **CI/CD** | GitHub Actions |

## Quick Start (Local Preview)

### Option A: Local Python preview (no Docker needed)

```bash
# 1. Create virtual environment
python3 -m venv /tmp/ml-auditor-venv
source /tmp/ml-auditor-venv/bin/activate

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Run migrations with SQLite (no PostgreSQL needed)
export DJANGO_SETTINGS_MODULE=config.settings_test
python manage.py migrate

# 4. Create a test user
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.create_user(email='test@test.com', username='test', password='test123')
print(f'Created: {u.email}')
"

# 5. Start the backend
python manage.py runserver 0.0.0.0:8000 &
BACKEND_PID=$!

# 6. Start the frontend
cd ../frontend
npm install --legacy-peer-deps 2>/dev/null
npm run dev &
FRONTEND_PID=$!

echo ""
echo "==========================================="
echo " ML-Auditor Preview Ready!"
echo "==========================================="
echo " Frontend:  http://localhost:3000"
echo " API:       http://localhost:8000/api/"
echo " Admin:     http://localhost:8000/admin/"
echo " Login:     test@test.com / test123"
echo "==========================================="
echo ""
echo "Press Ctrl+C to stop"
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
```

### Option B: Docker Compose (full stack)

```bash
# 1. Copy environment file
cp .env.example .env
# Edit .env with your API keys

# 2. Start all services
docker compose up -d

# 3. Run migrations
docker compose exec backend python manage.py migrate

# 4. Create superuser
docker compose exec backend python manage.py createsuperuser

# 5. Seed demo data (optional)
bash scripts/seed.sh

# 6. Access:
#    Frontend:  http://localhost:3000
#    API:       http://localhost:8000/api/
#    Admin:     http://localhost:8000/admin/
#    ML:        http://localhost:8001/docs
#    Grafana:   http://localhost:3001
#    Prometheus: http://localhost:9090
```

### Option C: Production deployment

```bash
# 1. Setup environment
cp .env.prod.example .env.prod
# Fill in all secrets in .env.prod

# 2. Start production stack
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 3. Setup SSL
bash scripts/setup-ssl.sh mlauditor.com admin@mlauditor.com

# 4. Run migrations
bash scripts/migrate.sh

# 5. Seed demo data
bash scripts/seed.sh
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/register` | Register new user |
| POST | `/api/users/login` | Login (JWT) |
| GET | `/api/users/me` | Get current user |

### Workspace
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/workspace/tasks` | List/Create tasks |
| PUT/DELETE | `/api/workspace/tasks/{id}` | Update/Delete task |
| PUT | `/api/workspace/tasks/{id}/move` | Move task between columns |
| GET/POST | `/api/workspace/events` | List/Create calendar events |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agents/chat` | Chat with AI agent |
| GET | `/api/agents/status` | Get agent status |
| GET/POST | `/api/agents/workflows` | List/Execute workflows |
| GET/PUT | `/api/agents/notifications/preferences` | Notification settings |

### Integrations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/integrations/status` | All integration statuses |
| POST | `/api/integrations/email/send` | Send email (IMAP) |
| GET | `/api/integrations/gmail/status` | Gmail connection status |
| GET | `/api/integrations/plaid/status` | Plaid connection status |
| POST | `/api/integrations/kijiji/search` | Search Kijiji listings |
| POST | `/api/integrations/canva/search` | Search Canva designs |

## Testing

```bash
# Backend (38 tests)
cd backend
DJANGO_SETTINGS_MODULE=config.settings_test pytest tests/ -v

# Frontend (13 tests)
cd frontend
npx vitest run

# Run all tests with coverage
cd backend
DJANGO_SETTINGS_MODULE=config.settings_test pytest --cov=apps --cov-report=term-missing
```

## Documentation

- [Phase 0 - Infrastructure](docs/PHASE_0_documentation.md)
- [Phase 1 - Backend API](docs/PHASE_1_documentation.md)
- [Phase 2 - Frontend](docs/PHASE_2_documentation.md)
- [Phase 3 - ML Service](docs/PHASE_3_documentation.md)
- [Architecture Spec](specs/ML_architecture.md)
- [Development Plan](specs/ML_master_plan.md)
- [Progress Tracker](docs/PROGRESS.md)

## Environment Variables

See `.env.prod.example` for all required variables. Key ones:

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret key (50+ chars) |
| `JWT_SECRET_KEY` | JWT signing key |
| `POSTGRES_PASSWORD` | Database password |
| `REDIS_PASSWORD` | Redis password |
| `NIM_API_KEY` | NVIDIA NIM API key |
| `PLAID_CLIENT_ID` | Plaid client ID |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client ID |
| `CANVA_CLIENT_ID` | Canva API client ID |

## License

Private - All rights reserved

## 🤖 Configuration des LLMs via UI

ML-Auditor permet de configurer **n'importe quel LLM** directement depuis l'interface utilisateur, sans modifier le code.

### Accéder à la configuration

1. Depuis le dashboard: Cliquer sur **Settings → LLM Configuration**
2. Ou aller directement à: `http://localhost:3001/dashboard/llm-config`

### Providers supportés

| Provider | Modèles | Configuration | Coût |
|----------|---------|---------------|------|
| **OpenAI** | GPT-4, GPT-4 Turbo, GPT-3.5 | Clef API d'OpenAI | Payant |
| **Anthropic** | Claude 3 Opus, Sonnet, Haiku | Clef API Anthropic | Payant |
| **NVIDIA NIM** | Llama 3.3, DeepSeek V3 | Clef API NVIDIA | Gratuit/Payant |
| **Ollama** | Llama2, Mistral, Neural Chat | Local (pas de clef) | Gratuit |
| **Hugging Face** | Modèles HF publics | Token HF | Gratuit/Payant |
| **Custom** | N'importe quel API | URL + clef personnalisée | Dépend |

### Exemple: Ajouter OpenAI GPT-4

1. **Provider**: OpenAI
2. **Nom**: "Mon GPT-4"
3. **Modèle**: `gpt-4`
4. **Clef API**: `sk-proj-xxxxx...` (obtenir à https://platform.openai.com/api-keys)
5. Cliquer **Test** pour vérifier la connexion ✓
6. Cliquer **Activer** pour utiliser ce LLM

### Exemple: Ajouter NVIDIA NIM (gratuit)

1. **Provider**: NVIDIA NIM
2. **Nom**: "NVIDIA Llama 3.3"
3. **Modèle**: `meta/llama-3.3-70b-instruct`
4. **Clef API**: `nvapi-xxxxx...` (obtenir à https://build.nvidia.com/)
5. **URL API**: `https://integrate.api.nvidia.com/v1` (pré-remplie)
6. Cliquer **Test** ✓

### Exemple: Ajouter Ollama (Local)

1. **Provider**: Ollama
2. **Nom**: "Ollama Local"
3. **Modèle**: `llama2` (ou votre modèle local)
4. **Clef API**: (vide pour Ollama)
5. **URL API**: `http://localhost:11434`
6. Avoir Ollama lancé: `ollama serve`

### Exemple: Ajouter API personnalisée

1. **Provider**: Custom
2. **Nom**: "Mon LLM privé"
3. **Modèle**: `mon-modele-v1`
4. **Clef API**: `votre-clef-secrete`
5. **URL API**: `https://mon-llm.example.com/v1`

### Fonctionnalités

- ✅ **Ajouter** plusieurs LLMs
- ✅ **Tester** la connexion avant activation
- ✅ **Activer** le LLM à utiliser (seul un LLM actif à la fois)
- ✅ **Supprimer** les LLMs non utilisés
- ✅ Les clefs API sont **chiffrées** en base de données (production)
- ✅ Chaque utilisateur a ses **propres configurations**
- ✅ Switch facile entre différents LLMs

### Sécurité

- Les clefs API ne sont **jamais** affichées après création
- Les clefs sont **chiffrées** en base de données (en production)
- Chaque utilisateur n'accède qu'à **ses propres LLMs**
- Les clefs ne sont **jamais loggées** ou exposées
- Utilise HTTPS en production

### API Endpoints pour LLM

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/integrations/llm-configurations/` | Lister tous les LLMs |
| POST | `/api/integrations/llm-configurations/` | Créer un nouveau LLM |
| GET | `/api/integrations/llm-configurations/{id}/` | Obtenir un LLM |
| PUT | `/api/integrations/llm-configurations/{id}/` | Modifier un LLM |
| DELETE | `/api/integrations/llm-configurations/{id}/` | Supprimer un LLM |
| POST | `/api/integrations/llm-configurations/{id}/test/` | Tester la connexion |
| POST | `/api/integrations/llm-configurations/{id}/set-active/` | Activer ce LLM |
| GET | `/api/integrations/llm-configurations/active/` | Obtenir le LLM actif |

### Obtenir les clefs API

**OpenAI:**
- Aller à https://platform.openai.com/api-keys
- Créer une nouvelle clef
- Copier: `sk-...`

**NVIDIA NIM (Gratuit):**
- Aller à https://build.nvidia.com/
- S'enregistrer avec Google ou GitHub
- Obtenir la clef: `nvapi-...`

**Anthropic (Claude):**
- Aller à https://console.anthropic.com/
- Créer une nouvelle clef

**Ollama (Local):**
- Télécharger: https://ollama.ai
- Lancer: `ollama serve`
- Pas de clef requise!

