"""
Request/response schemas for integration API.
"""

from typing import List, Optional

from pydantic import BaseModel


class OAuthCallbackSchema(BaseModel):
    code: str
    state: Optional[str] = None


# ─── Email (IMAP/SMTP) ──────────────────────────────────────────────


class IMAPConfigSchema(BaseModel):
    provider: str = "custom"
    imap_host: str
    imap_port: int = 993
    smtp_host: str
    smtp_port: int = 587
    password: str
    use_ssl: bool = True


class IMAPSendSchema(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    html: bool = False


# ─── Gmail (Google API) ─────────────────────────────────────────────


class EmailSendSchema(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None


# ─── Calendar ────────────────────────────────────────────────────────


class CalendarEventCreateSchema(BaseModel):
    summary: str
    start_time: str
    end_time: str
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None


# ─── Plaid ───────────────────────────────────────────────────────────


class PlaidExchangeSchema(BaseModel):
    public_token: str
    account_label: Optional[str] = None


# ─── Multi-account connections ────────────────────────────────────────


class IntegrationAccountCreateSchema(BaseModel):
    service: str
    account_label: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    extra_data: Optional[dict] = None


class IntegrationAccountUpdateSchema(BaseModel):
    account_label: Optional[str] = None
    is_active: Optional[bool] = None
    extra_data: Optional[dict] = None


# ─── Canva ───────────────────────────────────────────────────────────


class CanvaSearchSchema(BaseModel):
    keywords: List[str]
    category: Optional[str] = None


class CanvaCompetitorSchema(BaseModel):
    keywords: List[str]
    max_results: int = 20


# ─── Kijiji ──────────────────────────────────────────────────────────


class KijijiSearchSchema(BaseModel):
    query: str
    location: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None


# ─── Jira ─────────────────────────────────────────────────────────────


class JiraConfigureSchema(BaseModel):
    site_url: str
    email: str
    api_token: str


class JiraProjectSchema(BaseModel):
    id: str
    key: str
    name: str
    project_type_key: str
    lead: str
    avatar_url: str


class JiraIssueSchema(BaseModel):
    id: str
    key: str
    summary: str
    status: str
    priority: str
    issue_type: str
    assignee_display: str
    created: str
    updated: str
    due_date: Optional[str] = None
    url: str


class JiraSyncSchema(BaseModel):
    project_key: Optional[str] = None
    jql: Optional[str] = None
    max_results: int = 50


# ─── LLM Configuration ──────────────────────────────────────────────


class LLMConfigurationCreateSchema(BaseModel):
    provider: str
    name: str
    api_key: str
    model_name: str
    api_endpoint: Optional[str] = None


class LLMConfigurationUpdateSchema(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None


class LLMConfigurationResponseSchema(BaseModel):
    id: str
    provider: str
    name: str
    model_name: str
    api_endpoint: Optional[str] = None
    is_active: bool
    created_at: str


# ─── API Key Integrations ───────────────────────────────────────────


class ApiKeyCreateSchema(BaseModel):
    service: str
    label: str
    api_key: str
    api_secret: Optional[str] = ""
    extra_data: Optional[dict] = None


class ApiKeyUpdateSchema(BaseModel):
    label: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    extra_data: Optional[dict] = None
    is_active: Optional[bool] = None


class ApiKeyResponseSchema(BaseModel):
    id: str
    service: str
    label: str
    api_key_masked: str
    api_secret_masked: str
    extra_data: Optional[dict]
    is_active: bool
    status: str
    last_tested: Optional[str]
    last_error: str
    created_at: str
    updated_at: str


class ApiKeyTestResponseSchema(BaseModel):
    success: bool
    status: str
    error: Optional[str] = None


# ─── Integration Logs ───────────────────────────────────────────────


class IntegrationLogResponseSchema(BaseModel):
    id: str
    service: str
    level: str
    message: str
    metadata: Optional[dict]
    created_at: str
