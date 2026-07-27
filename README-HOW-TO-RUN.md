# How to Run ML-Auditor

Autonomous AI agent system for intelligent management of emails, calendars, banking data, and Kijiji marketplace.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend & ML service |
| Node.js | 18+ | Frontend |
| PostgreSQL | 16+ | Database (with pgvector extension) |
| Redis | 7+ | Cache, Celery broker, Channels |
| Docker | 24+ | (Option A + ELK) |
| Docker Compose | 2.20+ | (Option A) |

---

## Option A: Docker Compose (Recommended)

Everything runs in containers. No local installs needed beyond Docker.

```bash
cd ~/Desktop/ML-auditor

# Copy and edit environment variables
cp .env.example .env
# Edit .env — at minimum set NIM_API_KEY

# Start all services
docker compose up
```

**Services started:**

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Next.js dashboard |
| Backend API | http://localhost:8000/api/ | Django Ninja REST API |
| ML Service | http://localhost:8001/health | FastAPI ML microservice |
| Django Admin | http://localhost:8000/admin/ | Admin panel |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache & message broker |
| Elasticsearch | http://localhost:9200 | Log storage & search |
| Kibana | http://localhost:5601 | Log dashboard & visualization |
| Logstash | localhost:5044/9600 | Log pipeline |

**Useful commands:**

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f ml_service

# Stop all
docker compose down

# Stop and wipe data
docker compose down -v
```

---

## Option B: Local Development (without Docker)

Run each service manually in separate terminals.

### Step 1 — PostgreSQL Database

```bash
# Create the database
createdb mlauditor_db

# Enable pgvector extension
psql -d mlauditor_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Step 2 — Environment Variables

```bash
cd ~/Desktop/ML-auditor
cp .env.example .env
```

Edit `.env` and fill in at minimum:

```
DJANGO_SECRET_KEY=<random-50-char-string>
JWT_SECRET_KEY=<random-50-char-string>
NIM_API_KEY=nvapi-XXXX
```

### Step 3 — Backend (Django + Ninja)

```bash
cd ~/Desktop/ML-auditor/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start the dev server
python manage.py runserver
```

Backend is now at http://localhost:8000

### Step 4 — Celery Workers (Background Tasks)

Open two new terminals:

```bash
# Terminal 1 — Worker
cd ~/Desktop/ML-auditor/backend
source venv/bin/activate
celery -A config worker -l info -c 4

# Terminal 2 — Beat scheduler
cd ~/Desktop/ML-auditor/backend
source venv/bin/activate
celery -A config beat -l info
```

### Step 5 — ML Service (FastAPI)

```bash
cd ~/Desktop/ML-auditor/ml-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit env
cp .env.example .env
# Edit .env — set NIM_API_KEY

# Start the service
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

ML Service is now at http://localhost:8001

### Step 6 — Frontend (Next.js)

```bash
cd ~/Desktop/ML-auditor/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend is now at http://localhost:3000

---

## Option C: One-Command (Root package.json)

Uses `concurrently` to start Docker services and the frontend dev server together:

```bash
cd ~/Desktop/ML-auditor
npm install
npm run dev
```

---

## Logging & Monitoring (ELK Stack)

All services (Backend, ML Service, Frontend) write structured JSON logs.
Logs are stored in `logs/` and can be forwarded to Elasticsearch for
visualization in Kibana.

### Log Files

| Service | Log file | Written by |
|---------|----------|------------|
| Backend (Django) | `logs/backend/django.log` | Django JSON formatter + middleware |
| ML Service (FastAPI) | `logs/ml-service/ml-service.log` | structlog + JSON file handler |
| Frontend (Next.js) | `logs/frontend/frontend.log` | Frontend logger → `POST /api/logs/` |

### Log Entry Format

Every log entry is a JSON line with:

```json
{
  "@timestamp": "2026-07-25 01:08:56,381",
  "level": "INFO",
  "logger": "django.server",
  "message": "\"POST /api/users/login HTTP/1.1\" 200 609",
  "service": "backend",
  "stack": "django",
  "request_method": "POST",
  "request_path": "/api/users/login",
  "status_code": 200,
  "response_time": 42.5
}
```

**Fields present across all services:**

| Field | Description |
|-------|-------------|
| `@timestamp` | ISO 8601 timestamp |
| `level` | `INFO`, `WARNING`, `ERROR`, `DEBUG` |
| `message` | Human-readable log message |
| `service` | `backend`, `ml-service`, or `frontend` |
| `stack` | `django`, `fastapi`, or `nextjs` |

**Backend-specific fields:** `request_method`, `request_path`, `status_code`,
`response_time`, `ip_address`, `user_id`, `user_email`, `exception`

**ML-service-specific fields:** `agent_name`, `agent_action`, `nim_model`,
`search_query`, `search_results_count`

**Frontend-specific fields:** `endpoint`, `error_name`, `error_message`

### Option 1: ELK with Docker (Recommended)

Runs Elasticsearch, Logstash, and Kibana in containers.

```bash
# Start Elasticsearch
sudo docker run -d --name mlauditor_elasticsearch \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  -p 9200:9200 \
  docker.elastic.co/elasticsearch/elasticsearch:8.13.4

# Start Logstash (reads from logs/ directory)
sudo docker run -d --name mlauditor_logstash \
  -e "LS_JAVA_OPTS=-Xms256m -Xmx256m" \
  -v ~/Desktop/ML-auditor/docker/logstash/pipeline:/usr/share/logstash/pipeline:ro \
  -v ~/Desktop/ML-auditor/logs:/var/log/ml-auditor:ro \
  --network host \
  -p 5044:5044 -p 9600:9600 \
  docker.elastic.co/logstash/logstash:8.13.4

# Start Kibana
sudo docker run -d --name mlauditor_kibana \
  --network host \
  -e ELASTICSEARCH_HOSTS=http://127.0.0.1:9200 \
  -p 5601:5601 \
  docker.elastic.co/kibana/kibana:8.13.4
```

**Verify Elasticsearch is ready:**

```bash
curl http://localhost:9200/_cluster/health?pretty
```

**Wait 60-90 seconds** for Elasticsearch and Kibana to fully start.

**Access Kibana:** http://localhost:5601

### Option 2: ELK via Docker Compose (Full Stack)

If you have `docker compose` installed, start everything at once:

```bash
cd ~/Desktop/ML-auditor
sudo docker compose up -d elasticsearch logstash kibana
```

This starts all ELK services with proper networking and health checks.

### Option 3: Local Elasticsearch (No Docker)

For systems where Docker is unavailable:

```bash
# Ubuntu/Debian
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update && sudo apt install elasticsearch kibana
sudo systemctl start elasticsearch
sudo systemctl start kibana
```

Edit `/etc/elasticsearch/elasticsearch.yml` and add:

```yaml
discovery.type: single-node
xpack.security.enabled: false
```

Edit `/etc/kibana/kibana.yml` and set:

```yaml
elasticsearch.hosts: ["http://localhost:9200"]
```

### Setting Up Kibana Dashboards

1. Open http://localhost:5601
2. Go to **Management → Stack Management → Index Patterns**
3. Click **Create index pattern**
4. Create patterns for each service:
   - `ml-auditor-backend-*`
   - `ml-auditor-ml-service-*`
   - `ml-auditor-frontend-*`
5. Set `@timestamp` as the time field
6. Go to **Analytics → Discover**
7. Select an index pattern and explore logs

**Quick query examples in Kibana (KQL):**

```
service: backend
level: ERROR
service: ml-service AND message: agent
service: frontend AND level: warn
status_code >= 400
message: login AND service: backend
```

### Stopping ELK

```bash
sudo docker stop mlauditor_kibana mlauditor_logstash mlauditor_elasticsearch
sudo docker rm mlauditor_kibana mlauditor_logstash mlauditor_elasticsearch
```

### Viewing Logs Locally (Without ELK)

Logs are plain JSON lines — you can read them directly:

```bash
# Tail backend logs
tail -f logs/backend/django.log | python3 -m json.tool

# Tail ML service logs
tail -f logs/ml-service/ml-service.log | python3 -m json.tool

# Tail frontend logs
tail -f logs/frontend/frontend.log | python3 -m json.tool

# Filter for errors only
grep '"level": "ERROR"' logs/backend/django.log | python3 -m json.tool

# Search across all logs
grep -r "login" logs/*/
```

### ELK Ports Reference

| Service | Port | Purpose |
|---------|------|---------|
| Elasticsearch | 9200 | REST API & cluster communication |
| Logstash | 5044 | Beats input (Filebeat) |
| Logstash | 9600 | Logstash monitoring API |
| Kibana | 5601 | Web dashboard & visualization |

---

## Seed Demo Data

After the backend is running, populate with sample data:

```bash
cd ~/Desktop/ML-auditor
bash scripts/seed.sh
```

Creates:

- **Demo user**: `demo@mlauditor.com` / `demo123`
- **8 tasks** with various statuses and priorities
- **4 calendar events** (standup, bank review, dentist, Kijiji pickup)
- **Notification preferences**

---

## Environment Variables Reference

### Required

| Variable | Description | Where to get |
|----------|-------------|--------------|
| `DJANGO_SECRET_KEY` | Django signing key | Generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `JWT_SECRET_KEY` | JWT token signing key | Same as above |
| `NIM_API_KEY` | NVIDIA NIM API key for AI chat | https://build.nvidia.com |

### Optional (for integrations)

| Variable | Description | Where to get |
|----------|-------------|--------------|
| `PLAID_CLIENT_ID` | Plaid banking API client ID | https://dashboard.plaid.com |
| `PLAID_SECRET` | Plaid API secret | https://dashboard.plaid.com |
| `PLAID_ENV` | `sandbox` for dev, `production` for live | Plaid dashboard |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client ID | https://console.cloud.google.com |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth client secret | https://console.cloud.google.com |
| `CANVA_CLIENT_ID` | Canva Connect API client ID | https://www.canva.com/developers |
| `CANVA_CLIENT_SECRET` | Canva API client secret | https://www.canva.com/developers |
| `SENTRY_DSN` | Sentry error tracking DSN | https://sentry.io |
| `ML_SERVICE_URL` | ML microservice URL | Default: `http://localhost:8001` |

The app works without optional keys — chat falls back to a static response, integrations show "Not connected".

---

## Useful Commands

```bash
# Backend
python manage.py shell          # Django shell
python manage.py test           # Run backend tests
python manage.py createsuperuser # Create admin user

# Frontend
npm run lint        # Lint frontend code
npm run type-check  # TypeScript type checking
npm run test        # Run frontend tests

# Logs
tail -f logs/backend/django.log       # Watch backend logs
tail -f logs/ml-service/ml-service.log # Watch ML service logs
tail -f logs/frontend/frontend.log     # Watch frontend logs
grep '"level": "ERROR"' logs/backend/django.log  # Find errors

# ELK (Docker)
sudo docker ps --filter name=mlauditor_elasticsearch
sudo docker logs mlauditor_kibana
curl http://localhost:9200/_cluster/health?pretty

# Production
docker compose -f docker-compose.prod.yml up -d
bash scripts/setup-ssl.sh    # Set up SSL with Let's Encrypt
bash scripts/migrate.sh      # Zero-downtime database migration
```

---

## Troubleshooting

### "Email not configured" on the integrations page
Configure email via the Integrations panel: select provider, enter app password, click Connect.

### Chat returns "AI services are not configured"
Set your `NIM_API_KEY` in `.env`. Get a free key at https://build.nvidia.com.

### PostgreSQL connection refused
Make sure PostgreSQL is running: `sudo systemctl status postgresql`

### Redis connection refused
Make sure Redis is running: `sudo systemctl status redis`

### Port already in use
```bash
# Find process on port
lsof -i :8000
# Kill it
kill -9 <PID>
```

### Docker: "Cannot connect to the Docker daemon"
```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
# Then log out and back in
```

### Elasticsearch won't start (port 9200 in use)
```bash
# Find what's using port 9200
lsof -i :9200
# Stop existing Elasticsearch
sudo docker stop $(sudo docker ps -q --filter ancestor=elasticsearch)
# Or kill local process
sudo systemctl stop elasticsearch
```

### Kibana shows "Unable to connect"
- Elasticsearch must be running first. Wait 60-90 seconds after starting.
- Verify Elasticsearch: `curl http://localhost:9200/_cluster/health?pretty`
- Check Kibana logs: `sudo docker logs mlauditor_kibana`
- Ensure `ELASTICSEARCH_HOSTS` is set correctly.

### Logstash not picking up logs
- Check that `logs/` directory has `.log` files with JSON content.
- Verify Logstash config: `curl http://localhost:9600/_node/stats?pretty`
- Check Logstash logs: `sudo docker logs mlauditor_logstash`
- Ensure shared volume mount is correct (`logs/` → `/var/log/ml-auditor/`)

### Frontend logs not appearing
- The frontend sends logs to `POST /api/logs/`. Ensure the backend is running.
- Check browser console for `[LOG INFO]` / `[LOG ERROR]` entries.
- Logs are batched (20 entries or 5-second interval) before being sent.

### Docker permission denied
```bash
sudo usermod -aG docker $USER
newgrp docker
# Or prefix all docker commands with sudo
```
