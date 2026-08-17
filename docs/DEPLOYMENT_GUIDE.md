# ML-Auditor Deployment Guide

## Deployment Options

| Option | Best For | Complexity |
|--------|----------|-----------|
| Local preview | Development, testing | Low |
| Docker Compose | Small teams, staging | Medium |
| Kubernetes | Production, scaling | High |

## 1. Local Preview

```bash
# Quick test without Docker
cd backend
python3 -m venv /tmp/venv && source /tmp/venv/bin/activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings_test
python manage.py migrate && python manage.py runserver &

cd ../frontend
npm install --legacy-peer-deps && npm run dev
```

## 2. Docker Compose (Development)

```bash
cp .env.example .env
# Edit .env with your keys

docker compose up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

## 3. Docker Compose (Production)

```bash
cp .env.prod.example .env.prod
# Edit .env.prod with all secrets (or generate them):
bash scripts/generate_secrets.sh .env.prod

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Setup SSL
bash scripts/setup-ssl.sh mlauditor.com admin@mlauditor.com

# Run migrations
bash scripts/migrate.sh

# Seed demo data
bash scripts/seed.sh
```

## 4. Kubernetes

### Prerequisites
- Kubernetes 1.28+
- kubectl configured
- cert-manager installed (for SSL)

### Deploy

```bash
# 1. Create namespace
kubectl apply -f deployment/k8s/namespace.yml

# 2. Create secrets
kubectl create secret generic mlauditor-secrets \
  --namespace=mlauditor \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -base64 32) \
  --from-literal=REDIS_PASSWORD=$(openssl rand -base64 32) \
  --from-literal=DJANGO_SECRET_KEY=$(openssl rand -base64 50) \
  --from-literal=JWT_SECRET_KEY=$(openssl rand -base64 50) \
  --from-literal=SECRET_ENCRYPTION_KEY=$(openssl rand -base64 50) \
  --from-literal=JC_API_TOKEN=$(openssl rand -base64 50) \
  --from-literal=NIM_API_KEY=nvapi-XXXX

# 3. Deploy infrastructure
kubectl apply -f deployment/k8s/postgresql.yml
kubectl apply -f deployment/k8s/redis.yml

# 4. Run migrations
kubectl apply -f deployment/k8s/migrate-job.yml

# 5. Deploy app
kubectl apply -f deployment/k8s/backend.yml
kubectl apply -f deployment/k8s/ingress.yml
```

## SSL/TLS Setup

### Option A: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d mlauditor.com -d www.mlauditor.com

# Copy to deployment
cp /etc/letsencrypt/live/mlauditor.com/fullchain.pem deployment/nginx/ssl/
cp /etc/letsencrypt/live/mlauditor.com/privkey.pem deployment/nginx/ssl/
```

### Option B: Self-signed (Development)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deployment/nginx/ssl/privkey.pem \
  -out deployment/nginx/ssl/fullchain.pem \
  -subj "/CN=localhost"
```

## Zero-Downtime Migration

```bash
bash scripts/migrate.sh
```

Strategy: Creates shadow database → runs migrations → validates → swaps databases.

## Monitoring

### Prometheus (metrics)
```bash
# Access at http://localhost:9090
# Pre-configured scrape targets: backend, celery, ML, redis, postgres
```

### Grafana (dashboards)
```bash
# Access at http://localhost:3001
# Default login: admin / admin (change in .env.prod)
# Auto-provisioned: Prometheus + Loki datasources
```

### Loki (logs)
```bash
# Access at http://localhost:3100
# Aggregates container logs
```

### Sentry (errors)
```bash
# Set SENTRY_DSN in .env.prod
# Auto-captures Django exceptions
```

## Scaling

### Horizontal
```bash
# Scale backend replicas
docker compose -f docker-compose.prod.yml up -d --scale backend=3

# Kubernetes
kubectl scale deployment mlauditor-backend --replicas=3 -n mlauditor
```

### Workers
```bash
# Increase Celery concurrency
CELERY_WORKERS=8 docker compose -f docker-compose.prod.yml up -d celery_worker

# Increase Gunicorn workers
GUNICORN_WORKERS=8 docker compose -f docker-compose.prod.yml up -d backend
```

## Rollback

```bash
# Docker Compose
docker compose -f docker-compose.prod.yml rollback

# Kubernetes
kubectl rollout undo deployment/mlauditor-backend -n mlauditor
```

## Health Checks

| Service | Endpoint | Expected |
|---------|----------|----------|
| Backend | `GET /health` | 200 OK |
| MCP Server | `python -m apps.agents.mcp_server --http` | SSE connect |
| Frontend | `GET /` | 200 OK |
| PostgreSQL | `pg_isready` | ready |
| Redis | `redis-cli ping` | PONG |
