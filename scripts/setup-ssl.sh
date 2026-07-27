#!/usr/bin/env bash
# ML-Auditor SSL/TLS Setup with Let's Encrypt
# Prerequisites: domain pointed to server, certbot installed

set -euo pipefail

DOMAIN="${1:-mlauditor.com}"
EMAIL="${2:-admin@mlauditor.com}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== SSL/TLS Setup for $DOMAIN ==="

# 1. Stop nginx temporarily
docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" stop nginx

# 2. Get certificates via certbot
certbot certonly --standalone \
  -d "$DOMAIN" \
  -d "www.$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --non-interactive

# 3. Copy certificates to nginx ssl dir
mkdir -p "$PROJECT_DIR/deployment/nginx/ssl"
cp /etc/letsencrypt/live/"$DOMAIN"/fullchain.pem "$PROJECT_DIR/deployment/nginx/ssl/"
cp /etc/letsencrypt/live/"$DOMAIN"/privkey.pem "$PROJECT_DIR/deployment/nginx/ssl/"

# 4. Set proper permissions
chmod 600 "$PROJECT_DIR/deployment/nginx/ssl/privkey.pem"
chmod 644 "$PROJECT_DIR/deployment/nginx/ssl/fullchain.pem"

# 5. Restart nginx
docker compose -f "$PROJECT_DIR/docker-compose.prod.yml" start nginx

# 6. Setup auto-renewal cron
(ccrontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'docker compose -f $PROJECT_DIR/docker-compose.prod.yml restart nginx'") | crontab -

echo "✅ SSL/TLS setup complete for $DOMAIN"
echo "Auto-renewal cron job installed (runs daily at 3 AM)"
