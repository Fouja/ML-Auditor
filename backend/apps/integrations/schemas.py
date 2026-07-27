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
