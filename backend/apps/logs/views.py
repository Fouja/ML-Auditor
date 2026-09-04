"""
Client logs ingestion endpoint.

Accepts JSON log batches from the web frontend, mobile app, and desktop app.
Each entry is written to a per-service JSON-lines file under CLIENT_LOG_DIR and
also forwarded directly to the Logstash TCP input so it appears in Kibana
without waiting for Filebeat.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from config.logging_handlers import ship_json_lines_to_tcp

CLIENT_LOG_DIR = Path(
    os.environ.get(
        "CLIENT_LOG_DIR",
        Path(__file__).resolve().parent.parent.parent.parent / "logs" / "clients",
    )
)
CLIENT_LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGSTASH_TCP_HOST = os.environ.get("LOGSTASH_TCP_HOST", "localhost")
LOGSTASH_TCP_PORT = int(os.environ.get("LOGSTASH_TCP_PORT", "5000"))

frontend_logger = logging.getLogger("apps.frontend_logs")


ALLOWED_SERVICES = {
    "web",
    "desktop",
    "mobile",
    "frontend",  # kept for backward compatibility
}


def _normalize_service(entry: dict) -> str:
    """Return a clean service name from a client log entry."""
    service = str(entry.get("service", "web")).lower()
    if service in ALLOWED_SERVICES:
        return service
    # Unknown services still get their own file; this is a safety fallback.
    return service or "web"


@csrf_exempt
@require_POST
def ingest_frontend_logs(request):
    """
    Accepts a JSON body with { logs: [...] } and persists each entry.

    Entries are written to ``CLIENT_LOG_DIR/<service>/<service>.log`` as JSON
    lines and shipped to Logstash TCP in one batch.
    """
    try:
        body = json.loads(request.body)
        logs = body.get("logs", [])

        if not logs:
            return JsonResponse({"status": "ok", "received": 0})

        prepared_lines = []
        files_to_entries: dict[Path, list[dict]] = {}

        for entry in logs:
            if "@timestamp" not in entry:
                entry["@timestamp"] = datetime.now(timezone.utc).isoformat()

            service = _normalize_service(entry)
            stack = entry.get("stack") or {
                "web": "nextjs",
                "desktop": "tauri",
                "mobile": "react-native",
                "frontend": "nextjs",
            }.get(service, "client")
            entry["service"] = service
            entry["stack"] = stack

            log_file = CLIENT_LOG_DIR / service / f"{service}.log"
            files_to_entries.setdefault(log_file, []).append(entry)
            prepared_lines.append(json.dumps(entry, default=str))

        # Write per-service files.
        for log_file, entries in files_to_entries.items():
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a") as f:
                for entry in entries:
                    f.write(json.dumps(entry, default=str) + "\n")

        # Forward directly to Logstash for near-real-time dashboards.
        ship_json_lines_to_tcp(
            prepared_lines,
            host=LOGSTASH_TCP_HOST,
            port=LOGSTASH_TCP_PORT,
        )

        frontend_logger.info(
            "Ingested %d client log entries",
            len(logs),
            extra={"log_count": len(logs)},
        )

        return JsonResponse({"status": "ok", "received": len(logs)})

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
