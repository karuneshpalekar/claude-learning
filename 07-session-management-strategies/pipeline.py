"""Live session-management flows on the Claude Agent SDK.

  ClaudeAgentOptions(resume=<id>)                  -> continue a session
  ClaudeAgentOptions(resume=<id>, fork_session=True) -> branch it (divergent)
  ClaudeAgentOptions() + summary in the prompt      -> fresh start, no stale
                                                       tool results

Session id comes from `ResultMessage.session_id`. Name it with
`rename_session(session_id, "...")` (the SDK equivalent of the CLI's --name),
resume it with `resume=session_id` (the CLI's --resume).

Requires: pip install claude-agent-sdk + the Claude Code CLI + a key.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    fork_session,
    query,
    rename_session,
)


async def _run(prompt: str, options: ClaudeAgentOptions) -> tuple[str, str | None]:
    text_parts, session_id = [], None
    async for message in query(prompt=prompt, options=options):
        text_parts.append(str(message))
        if isinstance(message, ResultMessage):
            session_id = message.session_id
    return "\n".join(text_parts), session_id


async def initial_analysis(root: Path, name: str = "codebase-review-v1") -> str:
    opts = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep"],
        setting_sources=[],
        cwd=str(root),
    )
    prompt = (
        f"Analyse every .ts file under {root}/src. For each file report its issues "
        "with severity and line numbers, then give a structured summary "
        "(file -> issues -> recommendations)."
    )
    text, session_id = await _run(prompt, opts)
    if session_id:
        rename_session(session_id, name)          # <- CLI: --name
        print(f"[session {session_id} named {name!r}]")
    return text


async def naive_resume_after_edits(session_id: str) -> str:
    """DEMONSTRATES THE STALE-CONTEXT BUG. The session history still holds the
    pre-edit file contents as tool results."""
    opts = ClaudeAgentOptions(resume=session_id, allowed_tools=["Read"], setting_sources=[])
    text, _ = await _run(
        "I changed mod01.ts, mod03.ts and mod06.ts. Re-check them and tell me what still needs fixing.",
        opts,
    )
    return text


async def divergent_fork(session_id: str) -> str:
    """fork_session: explore an alternative direction without disturbing the
    original session (which someone else may still resume)."""
    opts = ClaudeAgentOptions(
        resume=session_id, fork_session=True, allowed_tools=["Read"], setting_sources=[]
    )
    text, _ = await _run("Explore a different refactor: what if mod03 used a queue abstraction?", opts)
    return text


async def fresh_start_with_summary(summary_block: str, root: Path, changed_files: list[str]) -> str:
    """The correct move after files changed: no resume, inject the summary,
    re-analyse ONLY the changed files."""
    opts = ClaudeAgentOptions(
        allowed_tools=["Read"], setting_sources=[], cwd=str(root),
    )
    files = ", ".join(changed_files)
    prompt = (
        f"{summary_block}\n\n"
        f"Those findings are from a prior session. Since then ONLY these files changed: "
        f"{files}. Re-read just those files from disk and tell me, consistently with the "
        f"summary, which of their issues are now resolved and which remain. Do not "
        f"re-analyse the unchanged files — trust the summary for those."
    )
    text, _ = await _run(prompt, opts)
    return text


if __name__ == "__main__":
    async def demo():
        root = Path(__file__).parent / "codebase"
        print(await initial_analysis(root))

    asyncio.run(demo())
