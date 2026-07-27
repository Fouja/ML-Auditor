# ML-Auditor Release Checklist

## Pre-Release

- [ ] All tests pass (backend 38/38, frontend 13/13)
- [ ] Code reviewed and approved
- [ ] No security vulnerabilities (`pip audit`, `npm audit`)
- [ ] Environment variables documented in `.env.prod.example`
- [ ] Database migrations tested on shadow database
- [ ] SSL certificates valid (not expiring within 30 days)
- [ ] Sentry configured and receiving errors
- [ ] Prometheus/Grafana dashboards accessible

## Deployment

- [ ] Backup current database
- [ ] Run `scripts/migrate.sh` for zero-downtime migration
- [ ] Deploy new Docker images
- [ ] Verify health checks pass (`GET /health`)
- [ ] Check Grafana dashboards for anomalies
- [ ] Verify WebSocket connections work
- [ ] Test login/register flow
- [ ] Test AI chat functionality
- [ ] Test email/calendar/Plaid integrations
- [ ] Verify Celery tasks are running

## Post-Deployment

- [ ] Monitor error rates for 1 hour
- [ ] Check Sentry for new issues
- [ ] Verify all cron jobs are scheduled
- [ ] Update release notes
- [ ] Tag release in git: `git tag -a v0.1.0 -m "Release 0.1.0"`
- [ ] Push tags: `git push origin v0.1.0`

## Rollback Plan

If critical issues detected:

1. Stop new containers: `docker compose -f docker-compose.prod.yml stop backend`
2. Restore database from backup
3. Start previous version: `docker compose -f docker-compose.prod.yml up -d backend`
4. Verify health checks
5. Notify team

## Version Numbering

- **Major** (X.0.0): Breaking API changes, database schema changes
- **Minor** (0.X.0): New features, non-breaking changes
- **Patch** (0.0.X): Bug fixes, security patches

## Release Notes Template

```markdown
# Release v0.X.0

## What's New
- Feature 1
- Feature 2

## Bug Fixes
- Fix 1
- Fix 2

## Security
- Security update 1

## Breaking Changes
- Change 1 (migration required)

## Known Issues
- Issue 1 (workaround: ...)
```
