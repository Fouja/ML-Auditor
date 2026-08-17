"""Data types for portfolio ingestion.

PageSnapshot is the crawl output (one per fetched page); _PortfolioProject and
_PortfolioExtract are the structured-output schema the LLM extraction fills.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


@dataclass
class PageSnapshot:
    url: str
    title: str = ""
    text: str = ""
    links: list[dict[str, str]] = field(default_factory=list)


class _PortfolioProject(BaseModel):
    title: str = ""
    stack: str = ""
    repo: str = ""
    impact: str = ""


class _PortfolioExtract(BaseModel):
    candidate_name: str = Field(default="", description="candidate name if visible")
    candidate_summary: str = Field(default="", description="2-4 sentence professional bio")
    skills: list[str] = Field(default_factory=list, description="tech skills explicitly visible")
    projects: list[_PortfolioProject] = Field(default_factory=list)
    experience: list[dict[str, str]] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
