"""JustHireMe MCP server over StreamableHTTP (mcp 2.x).

The repo's own ``mcp_server.py`` is a stdio-only, SDK-free JSON-RPC server.
This module exposes the same three tools through a real mcp 2.x MCPServer so the
ML-Auditor backend can call them over HTTP.

Endpoint:   http://<justhireme>:8788/mcp
Tools:      score_job_fit, evaluate_lead_quality, extract_lead_intel
"""

from __future__ import annotations

import asyncio
import json

from mcp.server.mcpserver import MCPServer

from mcp_server import TOOLS


def _tool_result_text(result) -> str:
    content = result.get("content") or []
    text = "".join(item.get("text", "") for item in content if item.get("type") == "text")
    return text or json.dumps(result, ensure_ascii=False, default=str)


def build_server() -> MCPServer:
    server = MCPServer(
        name="justhireme",
        title="JustHireMe",
        description="JustHireMe job intelligence: score job fit, evaluate lead quality, extract lead intel.",
        version="1.4.0",
    )

    @server.tool()
    def score_job_fit(posting: str, candidate: dict) -> str:
        """Score a job posting against a candidate profile using JustHireMe's explainable fit rubric."""
        return _tool_result_text(TOOLS["score_job_fit"]({"posting": posting, "candidate": candidate}))

    @server.tool()
    def evaluate_lead_quality(
        lead: dict,
        min_quality: int = 60,
        target_level: str = "beginner",
        max_age_days: int = 7,
    ) -> str:
        """Run the deterministic lead quality gate before saving or ranking a scraped job lead."""
        return _tool_result_text(
            TOOLS["evaluate_lead_quality"](
                {
                    "lead": lead,
                    "min_quality": min_quality,
                    "target_level": target_level,
                    "max_age_days": max_age_days,
                }
            )
        )

    @server.tool()
    def extract_lead_intel(text: str) -> str:
        """Extract company, location, budget, urgency, stack, and signal quality from raw lead text."""
        return _tool_result_text(TOOLS["extract_lead_intel"]({"text": text}))

    return server


def main() -> None:
    server = build_server()
    # Bridge: also expose the JobCamelonapp workbench's tools under peer_* so a
    # single MCP client of jobchameleon can call both apps' job intelligence.
    from mcp_bridge import register_peer_tools

    register_peer_tools(server, prefix="peer_", env_var="JCAPP_MCP_URL", peer_name="JobCamelonapp")
    asyncio.run(server.run_streamable_http_async(host="0.0.0.0", port=8788))


if __name__ == "__main__":
    main()
