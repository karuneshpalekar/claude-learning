"""MCP tool: customer_lookup, with on-demand failure modes.

Requires: pip install claude-agent-sdk

failure_mode:
  ""/"none"    -> normal: returns 1 record (or a valid empty result for an
                  unknown-but-well-formed id)
  "empty"      -> valid empty result: isError:false, resultCount:0  (NOT an error)
  "transient"  -> is_error envelope + {errorCategory:"transient",  isRetryable:true}
  "validation" -> is_error envelope + {errorCategory:"validation",  isRetryable:false}
  "business"   -> is_error envelope + {errorCategory:"business",    isRetryable:false}
  "permission" -> is_error envelope + {errorCategory:"permission",  isRetryable:false}
"""

from __future__ import annotations

import json
import re
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from errors import make_error, valid_empty_result

_DB = {"CUST-10001": {"id": "CUST-10001", "name": "Jane Doe", "tier": "gold"}}
_ID_RE = re.compile(r"^CUST-\d{5}$")


def _ok(payload: dict) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def _err(payload: dict) -> dict:
    # MCP envelope marks it an error; the text carries the structured metadata.
    return {"content": [{"type": "text", "text": json.dumps(payload)}], "is_error": True}


def lookup(identifier: str, failure_mode: str = "") -> dict:
    """Pure implementation, shared by the MCP handler and the offline tests."""
    mode = (failure_mode or "none").lower()

    if mode in {"transient", "validation", "business", "permission"}:
        return _err(make_error(mode))

    if mode == "empty":
        return _ok(valid_empty_result())

    # normal path
    if not _ID_RE.match(identifier or ""):
        return _err(make_error("validation"))
    rec = _DB.get(identifier)
    if rec is None:
        return _ok({"isError": False, "resultCount": 0, "results": []})
    return _ok({"isError": False, "resultCount": 1, "results": [rec]})


@tool(
    "customer_lookup",
    "Look up a customer by identifier (CUST-#####). Returns a structured result "
    "or a structured error {errorCategory, isRetryable, description}. Pass "
    "failure_mode to simulate a specific failure.",
    {"identifier": str, "failure_mode": str},
)
async def customer_lookup(args: dict[str, Any]) -> dict[str, Any]:
    return lookup(args["identifier"], args.get("failure_mode", ""))


SERVER = create_sdk_mcp_server(name="crm", version="1.0.0", tools=[customer_lookup])
TOOL_NAME = "mcp__crm__customer_lookup"
