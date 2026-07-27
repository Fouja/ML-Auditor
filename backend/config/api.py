"""
Main API configuration for ML-Auditor.
Uses Django Ninja for type-safe, auto-documented APIs.
"""

from ninja import NinjaAPI

from apps.users.auth import JWTAuth

# Create main API instance
api = NinjaAPI(
    title="ML-Auditor API",
    description="API for ML-Auditor - Autonomous AI Agent System",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    auth=JWTAuth(),
)

from apps.agents.api import router as agents_router
from apps.alerts.api import router as alerts_router
from apps.data_streams.api import router as data_streams_router
from apps.document_chunks.api import router as document_chunks_router

# Import and register routers
from apps.users.api import router as users_router
from apps.workspace.api import router as workspace_router

api.add_router("/users", users_router, tags=["Users"])
api.add_router("/data-streams", data_streams_router, tags=["Data Streams"])
api.add_router("/document-chunks", document_chunks_router, tags=["Document Chunks"])
api.add_router("/alerts", alerts_router, tags=["Alerts"])
api.add_router("/agents", agents_router, tags=["Agents"])
api.add_router("/workspace", workspace_router, tags=["Workspace"])

from apps.integrations.api import router as integrations_router

api.add_router("/integrations", integrations_router, tags=["Integrations"])
