"""
Shared logging utilities used by both server and desktop settings.

* JSONFormatter: emits structured JSON lines for Elasticsearch/Filebeat.
* TcpJsonLogHandler: ships JSON log lines directly to a Logstash TCP input.
  Useful for processes that run outside Docker (e.g. the Tauri desktop sidecar)
  and cannot be scraped by Filebeat.
"""

import json
import logging
import socket
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON log formatter for Elasticsearch ingestion.

    Records can override the default ``service`` / ``stack`` values by passing
    them in ``extra``. Extra attributes (including ``metrics`` dictionaries)
    are flattened into the top-level JSON object so Kibana can filter on them.
    """

    default_service = "backend"
    default_stack = "django"

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "@timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": getattr(record, "service", self.default_service),
            "stack": getattr(record, "stack", self.default_stack),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Request/context fields commonly attached by middleware.
        for attr in (
            "request_method",
            "request_path",
            "status_code",
            "user_id",
            "user_email",
            "ip_address",
            "response_time",
        ):
            value = getattr(record, attr, None)
            if value is not None:
                log_entry[attr] = value

        # Flatten metrics dictionaries (LLM health, integration health, etc.).
        metrics = getattr(record, "metrics", None)
        if isinstance(metrics, dict):
            for key, value in metrics.items():
                if key not in log_entry:
                    log_entry[key] = value

        # AI-agent fields.
        for attr in ("agent_name", "agent_action", "nim_model", "search_query", "search_results_count"):
            value = getattr(record, attr, None)
            if value is not None:
                log_entry[attr] = value

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, default=str)


class TcpJsonLogHandler(logging.Handler):
    """Fire-and-forget TCP handler that sends JSON Lines to Logstash.

    Each formatted record is sent as one newline-terminated JSON line to the
    configured ``host:port``. Connection failures are silently ignored so a
    missing Logstash instance does not crash the application.
    """

    def __init__(self, host: str = "localhost", port: int = 5000):
        super().__init__()
        self.host = host
        self.port = port

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record) + "\n"
            with socket.create_connection((self.host, self.port), timeout=2) as sock:
                sock.sendall(message.encode("utf-8"))
        except Exception:
            # Drop the log rather than breaking the app when Logstash is down.
            self.handleError(record)


def ship_json_lines_to_tcp(entries, host: str = "localhost", port: int = 5000, timeout: float = 2.0) -> None:
    """Ship a batch of pre-serialized JSON-line strings to Logstash TCP input.

    Used by the client-log ingestion endpoint to forward web/mobile/desktop
    logs directly to Logstash without waiting for Filebeat.
    """
    if not entries:
        return
    try:
        payload = "".join(f"{line}\n" for line in entries if line is not None)
        if not payload:
            return
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(payload.encode("utf-8"))
    except Exception:
        pass
