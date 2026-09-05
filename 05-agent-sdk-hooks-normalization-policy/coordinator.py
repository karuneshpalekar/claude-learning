"""Wires the MCP tools + hooks into ClaudeAgentOptions and runs a live query.

Requires: pip install claude-agent-sdk, the Claude Code CLI, and a valid key.
"""

from __future__ import annotations

import asyncio

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, query

from hooks import SessionState, make_block_large_refund, make_record_aml_result, make_require_aml_check, normalize_order_result
from mcp_tools import OPS_SERVER, TOOL_NAMES

SYSTEM_PROMPT = """
You are an operations agent. You have tools to check order status (three
backends, all normalised to the same shape by the time you see them),
process refunds, run AML checks, and transfer funds.

Refunds over $500 and fund transfers without a prior passing AML check on the
account are enforced by server-side controls you cannot see or override — if
one is blocked, explain the block to the user and route as instructed by the
error message rather than retrying the same call.
""".strip()

# Claude Code's hook matcher syntax: an exact tool name, or several joined
# with "|" (pipe-alternation) — not a glob.
ORDER_TOOLS_MATCHER = "mcp__ops__check_order_a|mcp__ops__check_order_b|mcp__ops__check_order_c"


def build_options(state: SessionState) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"ops": OPS_SERVER},
        allowed_tools=TOOL_NAMES,
        setting_sources=[],
        hooks={
            "PostToolUse": [
                HookMatcher(matcher=ORDER_TOOLS_MATCHER, hooks=[normalize_order_result]),
                HookMatcher(matcher="mcp__ops__aml_check", hooks=[make_record_aml_result(state)]),
            ],
            "PreToolUse": [
                HookMatcher(matcher="mcp__ops__process_refund", hooks=[make_block_large_refund(state)]),
                HookMatcher(matcher="mcp__ops__transfer_funds", hooks=[make_require_aml_check(state)]),
            ],
        },
    )


async def run(prompt: str) -> str:
    state = SessionState()
    options = build_options(state)
    chunks = []
    async for message in query(prompt=prompt, options=options):
        chunks.append(str(message))
    return "\n".join(chunks)


if __name__ == "__main__":
    print(asyncio.run(run(
        "Check the status of orders ORD-A1, ORD-B1, and ORD-C1, then summarise them "
        "consistently. Then try to refund $750 to ACC-1, and try to transfer $2000 from "
        "ACC-1 to an external account without running an AML check first."
    )))
