"""Hub coordinator built on the Claude Agent SDK.

Requirements the exam checks:

1. `allowed_tools` MUST contain "Agent" (a.k.a. "Task") — the hard gate for
   spawning any subagent. Without it the coordinator physically cannot delegate.
2. Subagents are defined under `options.agents` with scoped tools.
3. The coordinator collects the FULL structured findings from both research
   subagents and passes them, metadata intact, to the synthesis subagent.
4. The two research subagents are spawned IN PARALLEL — two Agent tool calls in
   a single coordinator turn — because they are independent (latency).

`fork_session` vs parallel Agent calls:
  - parallel Agent calls  -> N independent subagents, each its own fresh context,
                             running concurrently, results returned to the hub.
  - fork_session=True      -> resume ONE existing session under a new id so a
                             branch of that single conversation can diverge
                             without mutating the original. It is session
                             branching, not fan-out. Use Agent calls for
                             independent research; fork_session for
                             "what-if" continuations of one thread.
"""

from __future__ import annotations

import asyncio

from claude_agent_sdk import ClaudeAgentOptions, query

from subagent_defs import SUBAGENTS

COORDINATOR_SYSTEM = """
You are the RESEARCH COORDINATOR (central hub).

Procedure — follow exactly:
1. Split the topic into subtopics covering its full breadth.
2. For EACH subtopic, spawn the `web-search` and `document-analysis` subagents
   IN PARALLEL: emit both Agent tool calls in the SAME response. Never spawn them
   one after another and wait — they are independent.
3. Collect every subagent's COMPLETE structured findings (the full JSON array).
   Do NOT strip, truncate, or summarise the metadata fields
   (source_url, source_title, document_name, page_number, confidence, retrieved_by).
4. Concatenate all findings into one JSON array and pass that ENTIRE array to the
   `synthesis` subagent via a single Agent tool call. The synthesis agent has no
   retrieval tools; the metadata you pass is the only way it can cite anything.
5. Return the synthesis agent's cited report plus its `claims` array verbatim.

If the final report contains an unattributed claim, the fault is in step 3/4
(you dropped metadata), not in the synthesis agent.
""".strip()


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=COORDINATOR_SYSTEM,
        # (1) the hard gate — "Agent" is the current name, "Task" the alias.
        allowed_tools=["Agent", "Task", "TodoWrite"],
        # (2) scoped subagents
        agents=SUBAGENTS,
        setting_sources=[],   # programmatic config only
        permission_mode="acceptEdits",
    )


async def research(topic: str) -> str:
    options = build_options()
    prompt = (
        f"Research topic: {topic}\n\n"
        "Produce a fully-cited synthesis report. Spawn the two research subagents "
        "in parallel per subtopic, then pass all structured findings to the "
        "synthesis subagent with every metadata field preserved."
    )
    chunks: list[str] = []
    async for message in query(prompt=prompt, options=options):
        chunks.append(str(message))
    return "\n".join(chunks)


if __name__ == "__main__":
    print(asyncio.run(research("advances in solid-state batteries")))
