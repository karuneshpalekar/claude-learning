"""The two MCP tools, built with either the v1 or v2 descriptions.

Requires: pip install claude-agent-sdk
"""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from tool_specs import V1, V2

_CUSTOMERS = {"1002": {"account_id": "1002", "name": "Jane Doe", "email": "jane@example.com", "tier": "gold"}}
_ORDERS = {"ORD-5521": {"order_id": "ORD-5521", "status": "shipped", "total": 82.4, "eta": "2026-09-09"}}


def _text(payload: dict) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def build_server(version: str):
    specs = V1 if version == "v1" else V2

    @tool("get_customer", specs["get_customer"].render(), {"query": str})
    async def get_customer(args: dict[str, Any]) -> dict[str, Any]:
        return _text(next(iter(_CUSTOMERS.values())))

    @tool("lookup_order", specs["lookup_order"].render(), {"query": str})
    async def lookup_order(args: dict[str, Any]) -> dict[str, Any]:
        return _text(next(iter(_ORDERS.values())))

    return create_sdk_mcp_server(name="support", version="1.0.0", tools=[get_customer, lookup_order])


TOOL_NAMES = ["mcp__support__get_customer", "mcp__support__lookup_order"]
