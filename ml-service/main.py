"""
ML Service for ML-Auditor.
FastAPI application with CrewAI agents and NVIDIA NIM integration.
"""

import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import structlog

load_dotenv()

from app.api.routes import router
from app.services.database import init_db

import os as _os
LOG_DIR = _os.environ.get(
    "LOG_DIR",
    _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "logs", "ml-service"),
)
_os.makedirs(LOG_DIR, exist_ok=True)

class JSONFileHandler(logging.Handler):
    """Writes JSON log lines to a file for ELK ingestion."""

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self._stream = None

    def _get_stream(self):
        if self._stream is None or self._stream.closed:
            self._stream = open(self.filepath, "a")
        return self._stream

    def emit(self, record):
        try:
            log_entry = {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "service": "ml-service",
                "stack": "fastapi",
                "module": getattr(record, "module", record.module),
                "function": getattr(record, "funcName", ""),
                "line": getattr(record, "lineno", 0),
            }
            for key in ["request_method", "request_path", "status_code",
                         "response_time", "user_id", "trace_id",
                         "agent_name", "agent_action", "nim_model",
                         "embedding_model", "search_query", "search_results_count"]:
                if hasattr(record, key):
                    log_entry[key] = getattr(record, key)

            if record.exc_info and record.exc_info[0]:
                log_entry["exception"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1]),
                    "traceback": self.formatException(record.exc_info),
                }

            stream = self._get_stream()
            stream.write(json.dumps(log_entry, default=str) + "\n")
            stream.flush()
        except Exception:
            self.handleError(record)


json_file_handler = JSONFileHandler(f"{LOG_DIR}/ml-service.log")
json_file_handler.setLevel(logging.DEBUG)

stdlib_handler = logging.StreamHandler(sys.stdout)
stdlib_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s %(message)s"))

root_logger = logging.getLogger()
root_logger.addHandler(json_file_handler)
root_logger.addHandler(stdlib_handler)
root_logger.setLevel(logging.DEBUG)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

structlog_handler = logging.StreamHandler(sys.stdout)
structlog_handler.setFormatter(
    structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
        foreign_pre_chain=structlog.get_config()["processors"],
    )
)
logging.getLogger("structlog").addHandler(structlog_handler)
logging.getLogger("structlog").addHandler(json_file_handler)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting ML Service...")
    await init_db()
    logger.info("ML Service started successfully")
    yield
    logger.info("Shutting down ML Service...")


app = FastAPI(
    title="ML-Auditor ML Service",
    description="CrewAI agents and NVIDIA NIM integration for ML-Auditor",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    logger.info(
        "request",
        request_method=request.method,
        request_path=str(request.url.path),
        status_code=response.status_code,
        response_time=duration_ms,
    )
    return response


# Include routes
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ml-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
