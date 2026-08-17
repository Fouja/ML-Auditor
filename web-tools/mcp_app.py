"""
Agent-Reach MCP server — runs as its own process (port 8091) inside the
web-tools container so the ML-Auditor backend can consume it as a real MCP
client over StreamableHTTP.

Agent-Reach's bundled mcp_server.py targets the mcp<2 low-level API and is
stdio-only; this module is a protocol-compatible 2.x wrapper around the same
`doctor_report()`.

Endpoint:   http://<web-tools>:8091/mcp
Tools:      get_status
"""

import json
import asyncio

from mcp.server.mcpserver import MCPServer


def build_server() -> MCPServer:
    mcp_server = MCPServer(
        name="agent-reach",
        title="Agent Reach",
        description="Agent Reach status: which channels are installed and active.",
        version="1.0.0",
    )

    @mcp_server.tool()
    def get_status() -> str:
        from agent_reach.config import Config
        from agent_reach.core import AgentReach

        try:
            result = AgentReach(Config(read_only=True)).doctor_report()
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False, indent=2)
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    return mcp_server


def main() -> None:
    server = build_server()
    asyncio.run(
        server.run_streamable_http_async(host="0.0.0.0", port=8091)
    )


if __name__ == "__main__":
    main()
