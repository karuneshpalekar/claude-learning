"""Live Agent SDK wiring: the customer_lookup MCP tool + a system prompt that
tells the model the recovery policy per error category.

The deterministic reference implementation of that policy is `recovery_loop.recover`.

Requires: pip install claude-agent-sdk + the Claude Code CLI + a key.
"""

from __future__ import annotations

import asyncio

from claude_agent_sdk import ClaudeAgentOptions, query

from mcp_tools import SERVER, TOOL_NAME

RECOVERY_POLICY = """
You call customer_lookup. Every result is JSON. Branch on it:

- Success with resultCount >= 1  -> use the record.
- Success with resultCount == 0  -> report "no customer found". This is NOT an
  error. Do NOT retry it.
- Error {errorCategory:"transient", isRetryable:true} -> retry the SAME request,
  at most 3 times total, backing off between attempts. If it still fails, escalate.
- Error {errorCategory:"validation"} -> reformat the identifier to CUST-##### and
  resubmit once. Do not retry the original.
- Error {errorCategory:"business"} -> STOP. Escalate to a human; never retry.
- Error {errorCategory:"permission"} -> STOP. Ask for elevated credentials; never retry.
""".strip()


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=RECOVERY_POLICY,
        mcp_servers={"crm": SERVER},
        allowed_tools=[TOOL_NAME],
        setting_sources=[],
        max_turns=8,
    )


async def run(user_prompt: str) -> str:
    chunks = []
    async for message in query(prompt=user_prompt, options=build_options()):
        chunks.append(str(message))
    return "\n".join(chunks)


if __name__ == "__main__":
    print(asyncio.run(run(
        "Look up customer CUST-10001, but the first attempt will hit failure_mode='transient'. "
        "Recover appropriately."
    )))
