# ML-Auditor Operations Guide

## Service Management

### Docker Compose

```bash
# Start all services
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Stop all services
docker compose -f docker-compose.prod.yml down

# Restart a specific service
docker compose -f docker-compose.prod.yml restart backend

# View logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f celery_worker

# Check status
docker compose -f docker-compose.prod.yml ps
```

### Kubernetes

```bash
# Check pods
kubectl get pods -n mlauditor

# View logs
kubectl logs -f deployment/mlauditor-backend -n mlauditor

# Scale
kubectl scale deployment mlauditor-backend --replicas=3 -n mlauditor

# Rolling restart
kubectl rollout restart deployment/mlauditor-backend -n mlauditor
```

## Monitoring

### Key Metrics to Watch

| Metric | Warning Threshold | Critical Threshold |
|--------|------------------|-------------------|
| Backend response time | > 500ms | > 2000ms |
| Celery queue depth | > 100 tasks | > 500 tasks |
| PostgreSQL connections | > 80% pool | > 95% pool |
| Redis memory | > 70% maxmemory | > 90% maxmemory |
| Disk usage | > 80% | > 90% |
| Error rate | > 1% requests | > 5% requests |

### Grafana Dashboards

Access at `http://localhost:3001` (admin/grafana_password)

Pre-configured dashboards:
- Django Backend: Request rate, latency, errors
- Celery: Task throughput, queue depth, failure rate
- PostgreSQL: Connections, query time, cache hit ratio
- Redis: Memory, ops/sec, hit ratio

### Prometheus Alerts

```yaml
# deployment/prometheus/alerts.yml
groups:
  - name: mlauditor
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning

      - alert: CeleryQueueBacklog
        expr: celery_queue_length{queue!="default"} > 100
        for: 10m
        labels:
          severity: warning
```

## Incident Response

### Severity Levels

| Level | Response Time | Examples |
|-------|-------------|----------|
| P1 (Critical) | 15 min | Service down, data breach, authentication broken |
| P2 (High) | 1 hour | API errors > 5%, integration failures |
| P3 (Medium) | 4 hours | Performance degradation, non-critical feature broken |
| P4 (Low) | 24 hours | UI bugs, documentation updates |

### Incident Runbook

**Service Down (P1)**
1. Check container status: `docker compose ps`
2. Check logs: `docker compose logs --tail=100 backend`
3. Check database: `docker compose exec db pg_isready`
4. Check Redis: `docker compose exec redis redis-cli ping`
5. Restart affected service: `docker compose restart backend`
6. If persistent: Check Sentry for exceptions
7. Escalation: Notify team lead

**High Error Rate (P2)**
1. Check Sentry for new error patterns
2. Review recent deployments: `git log --oneline -10`
3. Check API rate limits: Review nginx logs
4. Check external service status (Plaid, Gmail, Canva)
5. Consider rollback if recent deploy

**Database Issues (P1/P2)**
1. Check connections: `SELECT count(*) FROM pg_stat_activity;`
2. Check for locks: `SELECT * FROM pg_locks WHERE NOT granted;`
3. Kill long queries: `SELECT pg_terminate_backend(pid);`
4. Check disk: `df -h`

**Memory/Performance (P3)**
1. Check container stats: `docker stats`
2. Check Redis memory: `redis-cli info memory`
3. Check PostgreSQL: `SELECT * FROM pg_stat_activity WHERE state = 'active';`
4. Scale workers if needed

### Backup Strategy

```bash
# Database backup (daily)
docker compose exec db pg_dump -U mlauditor mlauditor_db | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
gunzip -c backup_20260723.sql.gz | docker compose exec -T db psql -U mlauditor mlauditor_db
```

## Log Management

### Loki Queries (Grafana)

```
# All backend errors
{container="mlauditor_backend"} |~ "ERROR"

# Celery task failures
{container="mlauditor_celery_worker"} |~ "Task .* failed"

# API request latency
{container="mlauditor_backend"} | json | latency > 1000
```

### Log Retention

- Loki: 30 days
- Prometheus: 15 days
- Grafana: 90 days
- Application logs: Rotated daily, kept 30 days

## Security Operations

### Rotating Secrets

```bash
# Generate new secret
NEW_SECRET=$(openssl rand -base64 50)

# Update Kubernetes secret
kubectl create secret generic mlauditor-secrets \
  --namespace=mlauditor \
  --from-literal=DJANGO_SECRET_KEY=$NEW_SECRET \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods
kubectl rollout restart deployment/mlauditor-backend -n mlauditor
```

### SSL Certificate Renewal

```bash
# Auto-renewal via cron (installed by setup-ssl.sh)
# Manual renewal
certbot renew --post-hook "docker compose -f docker-compose.prod.yml restart nginx"
```

## Performance Tuning

### PostgreSQL

```sql
-- Check slow queries
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

-- Analyze table statistics
ANALYZE;

-- Reindex if needed
REINDEX DATABASE mlauditor_db;
```

### Redis

```bash
# Check key distribution
redis-cli --bigkeys

# Check memory usage
redis-cli info memory

# Flush cache if needed
redis-cli FLUSHDB
```

### Celery

```bash
# Monitor active tasks
celery -A config inspect active

# Monitor scheduled tasks
celery -A config inspect scheduled

# Purge queue
celery -A config purge
```
