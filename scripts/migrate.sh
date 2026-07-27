#!/usr/bin/env bash
# ML-Auditor Production Migration Script
# Zero-downtime migration strategy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== ML-Auditor Zero-Downtime Migration ==="

# 1. Create new database
echo "[1/6] Creating shadow database..."
NEW_DB="mlauditor_db_new_$(date +%Y%m%d_%H%M%S)"
docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T db \
  psql -U "${POSTGRES_USER:-mlauditor}" -d postgres -c "CREATE DATABASE $NEW_DB WITH TEMPLATE ${POSTGRES_DB:-mlauditor_db} OWNER ${POSTGRES_USER:-mlauditor};"

# 2. Run pending migrations on shadow DB
echo "[2/6] Running migrations on shadow database..."
docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T backend \
  sh -c "DJANGO_DATABASE_URL=postgres://${POSTGRES_USER:-mlauditor}:${POSTGRES_PASSWORD}@db:5432/$NEW_DB python manage.py migrate --noinput"

# 3. Validate migrations
echo "[3/6] Validating migrations..."
docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T backend \
  sh -c "DJANGO_DATABASE_URL=postgres://${POSTGRES_USER:-mlauditor}:${POSTGRES_PASSWORD}@db:5432/$NEW_DB python manage.py check --deploy"

# 4. Swap databases (rename old → backup, new → active)
echo "[4/6] Swapping databases..."
docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" exec -T db \
  psql -U "${POSTGRES_USER:-mlauditor}" -d postgres -c "
    SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${POSTGRES_DB:-mlauditor_db}' AND pid <> pg_backend_pid();
    ALTER DATABASE ${POSTGRES_DB:-mlauditor_db} RENAME TO ${POSTGRES_DB:-mlauditor_db}_backup_$(date +%Y%m%d_%H%M%S);
    ALTER DATABASE $NEW_DB RENAME TO ${POSTGRES_DB:-mlauditor_db};
  "

# 5. Restart backend to pick up new schema
echo "[5/6] Restarting backend..."
docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" restart backend celery_worker celery_beat

# 6. Verify
echo "[6/6] Verifying..."
sleep 5
HEALTH=$(curl -sf http://localhost/health || echo "FAIL")
if [ "$HEALTH" = "OK" ]; then
  echo "✅ Migration completed successfully!"
else
  echo "❌ Health check failed. Rollback with: ALTER DATABASE mlauditor_db RENAME TO mlauditor_db_failed; ALTER DATABASE <backup> RENAME TO mlauditor_db;"
  exit 1
fi

echo "=== Done ==="
