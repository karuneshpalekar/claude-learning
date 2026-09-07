"""Live version: run the 10 queries through a real Agent SDK session and log
which tool the model actually selects, for v1 vs v2 descriptions.

Requires: pip install claude-agent-sdk + the Claude Code CLI + a key.
"""

from __future__ import annotations

import asyncio

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ToolUseBlock, query

from mcp_tools import TOOL_NAMES, build_server
from queries import QUERIES
from system_prompt_audit import SYSTEM_PROMPT_V2


def build_options(version: str, system_prompt: str = SYSTEM_PROMPT_V2) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        mcp_servers={"support": build_server(version)},
        allowed_tools=TOOL_NAMES,
        setting_sources=[],
        max_turns=2,   # we only care about the FIRST tool choice
    )


async def first_tool_selected(user_query: str, options: ClaudeAgentOptions) -> str | None:
    async for message in query(prompt=user_query, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    return block.name.replace("mcp__support__", "")
    return None


async def run_suite(version: str) -> list[tuple[str, str, str | None]]:
    options = build_options(version)
    out = []
    for q, expected in QUERIES:
        pick = await first_tool_selected(q, options)
        out.append((q, expected, pick))
    return out


async def main() -> None:
    for version in ("v1", "v2"):
        results = await run_suite(version)
        correct = sum(1 for _q, exp, pick in results if pick == exp)
        print(f"\n=== {version} descriptions: {correct}/{len(results)} ===")
        for q, exp, pick in results:
            flag = "" if pick == exp else "  <- misrouted"
            print(f"  {q[:46]:<46} expected={exp:<13} got={pick}{flag}")


if __name__ == "__main__":
    asyncio.run(main())
