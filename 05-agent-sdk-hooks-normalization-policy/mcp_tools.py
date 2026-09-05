"""Custom MCP tools for the ops agent.

- check_order_a/b/c: same underlying fact ("order status"), three different
  wire formats — this is the data-format-chaos scenario the hooks fix.
- process_refund: policy-gated by amount (PreToolUse).
- transfer_funds / aml_check: policy-gated by a session prerequisite (PreToolUse).

Requires: pip install claude-agent-sdk
"""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

# --- mock backends ----------------------------------------------------------

_ORDERS_A = {"ORD-A1": {"order_id": "ORD-A1", "timestamp": 1735689600, "status_code": 2}}
_ORDERS_B = {"ORD-B1": {"order_id": "ORD-B1", "date": "2025-06-15T00:00:00Z", "status": "Completed"}}
_ORDERS_C = {"ORD-C1": {"order_id": "ORD-C1", "date": "03/11/2025", "status": "P"}}  # 3 Nov 2025, pending

_ACCOUNTS = {"ACC-1": {"balance": 10_000.0}}


def _text(payload: dict) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


@tool("check_order_a", "Legacy system: order status via epoch timestamp + numeric code.",
      {"order_id": str})
async def check_order_a(args: dict[str, Any]) -> dict[str, Any]:
    return _text(_ORDERS_A.get(args["order_id"], {"error": "not_found"}))


@tool("check_order_b", "Modern system: order status via ISO 8601 date + English status.",
      {"order_id": str})
async def check_order_b(args: dict[str, Any]) -> dict[str, Any]:
    return _text(_ORDERS_B.get(args["order_id"], {"error": "not_found"}))


@tool("check_order_c", "Partner feed: order status via DD/MM/YYYY date + single-char code.",
      {"order_id": str})
async def check_order_c(args: dict[str, Any]) -> dict[str, Any]:
    return _text(_ORDERS_C.get(args["order_id"], {"error": "not_found"}))


@tool("process_refund", "Refund an amount to an account. Auto-approved under $500; "
      "larger amounts require human escalation (enforced by a PreToolUse hook).",
      {"account_id": str, "amount": float})
async def process_refund(args: dict[str, Any]) -> dict[str, Any]:
    return _text({"status": "refunded", "account_id": args["account_id"], "amount": args["amount"]})


@tool("transfer_funds", "Transfer funds out of an account. Requires a passing aml_check "
      "in this session first (enforced by a PreToolUse hook).",
      {"account_id": str, "amount": float, "destination": str})
async def transfer_funds(args: dict[str, Any]) -> dict[str, Any]:
    return _text({"status": "transferred", **args})


@tool("aml_check", "Run an anti-money-laundering check on an account.", {"account_id": str})
async def aml_check(args: dict[str, Any]) -> dict[str, Any]:
    # Toy rule: any account starting with "ACC-" passes; used to show the
    # pass path. A real check would call a compliance service.
    result = "pass" if args["account_id"].startswith("ACC-") else "fail"
    return _text({"account_id": args["account_id"], "result": result})


OPS_SERVER = create_sdk_mcp_server(
    name="ops",
    version="1.0.0",
    tools=[check_order_a, check_order_b, check_order_c, process_refund, transfer_funds, aml_check],
)

# mcp__<server>__<tool> naming, per the SDK convention.
TOOL_NAMES = [
    "mcp__ops__check_order_a",
    "mcp__ops__check_order_b",
    "mcp__ops__check_order_c",
    "mcp__ops__process_refund",
    "mcp__ops__transfer_funds",
    "mcp__ops__aml_check",
]
