#!/usr/bin/env bash
# Generate strong secrets for the ML-Auditor stack.
#
# Idempotent: existing values in the target env file are left untouched;
# only missing (or empty) keys are generated and filled.
#
# Usage:  scripts/generate_secrets.sh [path-to-env-file]
#         (defaults to ./.env)

set -euo pipefail

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "error: $ENV_FILE not found. Copy .env.example first:" >&2
  echo "  cp .env.example $ENV_FILE" >&2
  exit 1
fi

generate() {
  python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(50)))"
}

set_if_empty() {
  local key="$1"
  if grep -qE "^${key}=.+" "$ENV_FILE"; then
    echo "kept existing  ${key}"
  elif grep -qE "^${key}=$" "$ENV_FILE"; then
    local value
    value="$(generate)"
    python3 - "$ENV_FILE" "$key" "$value" <<'PY'
import sys
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
lines = []
with open(path) as f:
    for line in f:
        if line.startswith(key + "="):
            lines.append(f"{key}={value}\n")
        else:
            lines.append(line)
with open(path, "w") as f:
    f.writelines(lines)
PY
    echo "generated       ${key}"
  else
    local value
    value="$(generate)"
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
    echo "generated       ${key}"
  fi
}

set_if_empty DJANGO_SECRET_KEY
set_if_empty JWT_SECRET_KEY
set_if_empty SECRET_ENCRYPTION_KEY
set_if_empty JC_API_TOKEN

echo
echo "Done. Restart the stack so the new secrets take effect:"
echo "  docker compose up -d --force-recreate"
echo
echo "Never commit $ENV_FILE. Rotate any key you believe may have leaked."
