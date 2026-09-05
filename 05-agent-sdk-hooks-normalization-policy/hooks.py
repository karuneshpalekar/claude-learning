"""PostToolUse (normalisation) and PreToolUse (policy) hooks.

Written against the ACTUAL installed `claude-agent-sdk` (0.2.152) callback
contract, not a guessed one:

  callback(input_data: dict, tool_use_id: str | None, context: HookContext)
      -> dict   # a SyncHookJSONOutput-shaped dict

  input_data (PreToolUseHookInput / PostToolUseHookInput, both TypedDicts —
  plain dicts at runtime) carries: tool_name, tool_input, and — PostToolUse
  only — tool_response. To act, return
  {"hookSpecificOutput": {"hookEventName": "PreToolUse"|"PostToolUse", ...}}.
  Returning {} means "no opinion, allow / don't change anything".

Direction matters and the exam tests it directly:
  - PostToolUse runs AFTER the tool executed, before the model sees the
    result -> correct for normalising data shape via `updatedMCPToolOutput`.
    It cannot undo a side-effect, so it must never be used to "block"
    anything.
  - PreToolUse runs BEFORE the tool executes and can set
    `permissionDecision: "deny"` -> the ONLY correct place to enforce a
    policy that must never fire (a refund over the limit, a transfer with no
    AML check). By the time a PostToolUse hook would see the result,
    process_refund/transfer_funds already happened.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from normalize import normalize_record_from_tool

REFUND_LIMIT = 500.0

ORDER_TOOLS = {"mcp__ops__check_order_a", "mcp__ops__check_order_b", "mcp__ops__check_order_c"}
REFUND_TOOL = "mcp__ops__process_refund"
TRANSFER_TOOL = "mcp__ops__transfer_funds"
AML_TOOL = "mcp__ops__aml_check"


@dataclass
class SessionState:
    """Server-side, per-session state the hooks read/write. The model never
    writes to this directly."""

    aml_passed_accounts: set[str] = field(default_factory=set)
    blocked_refunds: list[dict] = field(default_factory=list)
    blocked_transfers: list[dict] = field(default_factory=list)


def _parse_mcp_result_json(tool_response: Any) -> dict | None:
    """MCP tool responses have the shape {"content": [{"type": "text", "text": "..."}]}."""
    try:
        return json.loads(tool_response["content"][0]["text"])
    except Exception:
        return None


def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


# --- PostToolUse: normalisation ---------------------------------------------

async def normalize_order_result(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
    """Runs after check_order_a/b/c. Converts whichever wire format that tool
    used into the canonical {order_id, date (ISO 8601), status (English)}."""
    tool_name = input_data["tool_name"]
    if tool_name not in ORDER_TOOLS:
        return {}
    raw = _parse_mcp_result_json(input_data.get("tool_response"))
    if raw is None or "error" in raw:
        return {}
    normalized = normalize_record_from_tool(tool_name, raw)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedMCPToolOutput": {"content": [{"type": "text", "text": json.dumps(normalized)}]},
        }
    }


# --- PreToolUse: policy enforcement -----------------------------------------

def make_block_large_refund(state: SessionState):
    async def block_large_refund(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        tool_name, tool_input = input_data["tool_name"], input_data["tool_input"]
        if tool_name != REFUND_TOOL:
            return {}
        amount = float(tool_input.get("amount", 0))
        if amount > REFUND_LIMIT:
            state.blocked_refunds.append(dict(tool_input))
            return _deny(
                f"process_refund blocked: ${amount:.2f} exceeds the ${REFUND_LIMIT:.0f} "
                "auto-approval limit. Routed to human escalation queue."
            )
        return {}

    return block_large_refund


def make_require_aml_check(state: SessionState):
    async def require_aml_check(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        tool_name, tool_input = input_data["tool_name"], input_data["tool_input"]
        if tool_name != TRANSFER_TOOL:
            return {}
        account_id = tool_input.get("account_id", "")
        if account_id not in state.aml_passed_accounts:
            state.blocked_transfers.append(dict(tool_input))
            return _deny(
                f"transfer_funds blocked: no passing aml_check on file for "
                f"account {account_id!r} in this session. Run aml_check first."
            )
        return {}

    return require_aml_check


def make_record_aml_result(state: SessionState):
    """PostToolUse companion: records a PASS from aml_check into session state
    so the PreToolUse gate above can read it. Never blocks anything itself —
    recording facts is a PostToolUse job; enforcing on them is PreToolUse's."""

    async def record_aml_result(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        tool_name = input_data["tool_name"]
        if tool_name != AML_TOOL:
            return {}
        raw = _parse_mcp_result_json(input_data.get("tool_response"))
        if raw and raw.get("result") == "pass":
            state.aml_passed_accounts.add(input_data["tool_input"].get("account_id", ""))
        return {}

    return record_aml_result
