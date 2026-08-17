"""
Logs ingestion endpoint for frontend logs.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import os

FRONTEND_LOG_DIR = Path(
    os.environ.get(
        "FRONTEND_LOG_DIR",
        Path(__file__).resolve().parent.parent.parent.parent / "logs" / "frontend",
    )
)
FRONTEND_LOG_DIR.mkdir(parents=True, exist_ok=True)

frontend_logger = logging.getLogger("apps.frontend_logs")


@csrf_exempt
@require_POST
def ingest_frontend_logs(request):
    """
    Accepts a JSON body with { logs: [...] } and appends each entry
    to logs/frontend.log as JSON lines.
    """
    try:
        body = json.loads(request.body)
        logs = body.get("logs", [])

        if not logs:
            return JsonResponse({"status": "ok", "received": 0})

        log_file = FRONTEND_LOG_DIR / "frontend.log"
        with open(log_file, "a") as f:
            for entry in logs:
                if "@timestamp" not in entry:
                    entry["@timestamp"] = datetime.now(timezone.utc).isoformat()
                entry["service"] = "frontend"
                entry["stack"] = "nextjs"
                f.write(json.dumps(entry, default=str) + "\n")

        frontend_logger.info(
            "Ingested %d frontend log entries",
            len(logs),
            extra={"log_count": len(logs)},
        )

        return JsonResponse({"status": "ok", "received": len(logs)})

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
