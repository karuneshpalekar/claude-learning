"""Offline tests. Hook handlers are plain async functions taking
(input_data: dict, tool_use_id, context) — the real claude-agent-sdk callback
shape — so they're tested directly with hand-built input_data dicts. No live
model call needed to verify their logic.
"""

from __future__ import annotations

import asyncio
import json

from hooks import (
    SessionState,
    make_block_large_refund,
    make_record_aml_result,
    make_require_aml_check,
    normalize_order_result,
)
from mcp_tools import check_order_a, check_order_b, check_order_c, process_refund, transfer_funds, aml_check
from normalize import (
    char_status_to_english,
    ddmmyyyy_to_iso_date,
    iso_datetime_to_iso_date,
    numeric_status_to_english,
    unix_to_iso_date,
)

A, B, C = "mcp__ops__check_order_a", "mcp__ops__check_order_b", "mcp__ops__check_order_c"
REFUND, TRANSFER, AML = "mcp__ops__process_refund", "mcp__ops__transfer_funds", "mcp__ops__aml_check"


def _run(coro):
    return asyncio.run(coro)


def _pre_input(tool_name: str, tool_input: dict) -> dict:
    return {"tool_name": tool_name, "tool_input": tool_input, "tool_use_id": "tu_1"}


def _post_input(tool_name: str, tool_input: dict, tool_response: dict) -> dict:
    return {"tool_name": tool_name, "tool_input": tool_input, "tool_response": tool_response, "tool_use_id": "tu_1"}


# --- 1. pure normalisation unit tests ------------------------------------

def test_normalize_units():
    assert unix_to_iso_date(1735689600) == "2025-01-01"
    assert iso_datetime_to_iso_date("2025-06-15T00:00:00Z") == "2025-06-15"
    assert ddmmyyyy_to_iso_date("03/11/2025") == "2025-11-03"   # 3 Nov, not 3rd month
    assert numeric_status_to_english(2) == "completed"
    assert char_status_to_english("P") == "pending"
    print("normalize.py unit conversions correct")


# --- 2. PostToolUse normalises all three tool-result formats --------------

def test_post_tool_use_normalizes_all_three_formats():
    async def scenario():
        raw_a = await check_order_a.handler({"order_id": "ORD-A1"})
        raw_b = await check_order_b.handler({"order_id": "ORD-B1"})
        raw_c = await check_order_c.handler({"order_id": "ORD-C1"})

        norm_a = await normalize_order_result(_post_input(A, {"order_id": "ORD-A1"}, raw_a), "tu1", None)
        norm_b = await normalize_order_result(_post_input(B, {"order_id": "ORD-B1"}, raw_b), "tu2", None)
        norm_c = await normalize_order_result(_post_input(C, {"order_id": "ORD-C1"}, raw_c), "tu3", None)
        return norm_a, norm_b, norm_c

    norm_a, norm_b, norm_c = _run(scenario())

    def payload(hook_result):
        blocks = hook_result["hookSpecificOutput"]["updatedMCPToolOutput"]["content"]
        return json.loads(blocks[0]["text"])

    pa, pb, pc = payload(norm_a), payload(norm_b), payload(norm_c)

    for p in (pa, pb, pc):
        assert set(p) == {"order_id", "date", "status"}
        assert len(p["date"]) == 10 and p["date"][4] == "-" and p["date"][7] == "-"  # ISO 8601
        assert p["status"] in {"pending", "processing", "completed", "failed", "cancelled"}  # English word

    assert pa["date"] == "2025-01-01" and pa["status"] == "completed"
    assert pb["date"] == "2025-06-15" and pb["status"] == "completed"
    assert pc["date"] == "2025-11-03" and pc["status"] == "pending"  # not misread day/month
    print("all three tool formats normalised to identical {date, status} shape")


# --- 3. PreToolUse blocks refunds over the threshold -----------------------

def test_pre_tool_use_blocks_large_refund_only():
    state = SessionState()
    hook = make_block_large_refund(state)

    big = _run(hook(_pre_input(REFUND, {"account_id": "ACC-1", "amount": 750.0}), "tu1", None))
    small = _run(hook(_pre_input(REFUND, {"account_id": "ACC-1", "amount": 200.0}), "tu2", None))

    assert big["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "500" in big["hookSpecificOutput"]["permissionDecisionReason"]
    assert small == {}   # {} == allow, no opinion
    assert state.blocked_refunds == [{"account_id": "ACC-1", "amount": 750.0}]
    print("refund > $500 blocked pre-execution; refund <= $500 allowed")


# --- 4. PreToolUse blocks transfer_funds until aml_check passes ------------

def test_pre_tool_use_blocks_transfer_until_aml_pass():
    state = SessionState()
    pre = make_require_aml_check(state)
    post = make_record_aml_result(state)

    transfer_input = {"account_id": "ACC-1", "amount": 2000.0, "destination": "EXT-9"}

    before = _run(pre(_pre_input(TRANSFER, transfer_input), "tu1", None))
    assert before["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "aml_check" in before["hookSpecificOutput"]["permissionDecisionReason"]

    aml_result = _run(aml_check.handler({"account_id": "ACC-1"}))
    _run(post(_post_input(AML, {"account_id": "ACC-1"}, aml_result), "tu2", None))

    after = _run(pre(_pre_input(TRANSFER, transfer_input), "tu3", None))
    assert after == {}  # allowed now
    assert state.blocked_transfers == [transfer_input]
    print("transfer blocked before aml_check; allowed after a passing aml_check is on record")


# --- 5/6. the blocked tool NEVER executes ---------------------------------

async def _dispatch(tool_name, tool_input, executor, pre_hooks):
    """Minimal stand-in for what the Agent SDK's harness does: run every
    matching PreToolUse hook; only call the real executor if none deny."""
    for hook in pre_hooks:
        result = await hook(_pre_input(tool_name, tool_input), "tu", None)
        spec = result.get("hookSpecificOutput", {})
        if spec.get("permissionDecision") == "deny":
            return {"executed": False, "message": spec["permissionDecisionReason"]}
    return {"executed": True, "result": await executor(tool_input)}


def test_blocked_operations_never_execute():
    state = SessionState()
    refund_hook = make_block_large_refund(state)
    transfer_hook = make_require_aml_check(state)

    calls = {"refund": 0, "transfer": 0}

    async def counting_refund(args):
        calls["refund"] += 1
        return await process_refund.handler(args)

    async def counting_transfer(args):
        calls["transfer"] += 1
        return await transfer_funds.handler(args)

    blocked_refund = _run(_dispatch(
        REFUND, {"account_id": "ACC-1", "amount": 750.0}, counting_refund, [refund_hook]
    ))
    blocked_transfer = _run(_dispatch(
        TRANSFER, {"account_id": "ACC-1", "amount": 2000.0, "destination": "EXT-9"},
        counting_transfer, [transfer_hook]
    ))

    assert blocked_refund["executed"] is False
    assert blocked_transfer["executed"] is False
    assert calls == {"refund": 0, "transfer": 0}, "the underlying tool must never run when denied"

    # Now satisfy prerequisites and confirm both succeed.
    ok_refund = _run(_dispatch(
        REFUND, {"account_id": "ACC-1", "amount": 200.0}, counting_refund, [refund_hook]
    ))
    aml_result = _run(aml_check.handler({"account_id": "ACC-1"}))
    _run(make_record_aml_result(state)(_post_input(AML, {"account_id": "ACC-1"}, aml_result), "tu", None))
    ok_transfer = _run(_dispatch(
        TRANSFER, {"account_id": "ACC-1", "amount": 2000.0, "destination": "EXT-9"},
        counting_transfer, [transfer_hook]
    ))

    assert ok_refund["executed"] is True and calls["refund"] == 1
    assert ok_transfer["executed"] is True and calls["transfer"] == 1
    print("blocked calls never reached the executor (0 calls); satisfied calls executed exactly once")


if __name__ == "__main__":
    test_normalize_units()
    test_post_tool_use_normalizes_all_three_formats()
    test_pre_tool_use_blocks_large_refund_only()
    test_pre_tool_use_blocks_transfer_until_aml_pass()
    test_blocked_operations_never_execute()
    print("\nAll tests passed.")
