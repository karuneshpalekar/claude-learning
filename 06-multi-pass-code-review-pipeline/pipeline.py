"""Live multi-pass review pipeline on the Claude Agent SDK.

Architecture (the exam's point — dilution is structural, so the fix is structural):

  single_pass_review(dir)   -> ONE query, all N files in context. Baseline that
                               shows attention dilution: deep on early files,
                               shallow/absent on later ones.

  multi_pass_review(dir)    -> layer 1: a `file-reviewer` subagent PER FILE, each
                               with the full attention budget and an identical
                               structured-output contract.
                               layer 2: a `cross-file-integrator` subagent that
                               receives every per-file summary and looks only for
                               cross-cutting issues (data flow, API consistency,
                               pattern-usage consistency).

Requires: pip install claude-agent-sdk + the Claude Code CLI + a key.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query

FILE_REVIEWER = AgentDefinition(
    description="Reviews exactly one source file in full depth and returns structured findings.",
    prompt=(
        "You review ONE file. Read it and report EVERY issue with this exact JSON shape:\n"
        '{"file": str, "bug_count": int, "severity_breakdown": {"high": int, "medium": int, '
        '"low": int}, "findings": [{"line": int, "rule": str, "severity": '
        '"high"|"medium"|"low", "message": str}]}\n'
        "Give this file your complete attention regardless of how large the project is. "
        "Do not summarise or skip — one file, full depth."
    ),
    tools=["Read"],
    model="sonnet",
    maxTurns=4,
)

CROSS_FILE_INTEGRATOR = AgentDefinition(
    description="Finds cross-cutting issues from the collected per-file summaries. No file reading.",
    prompt=(
        "You receive a JSON array of per-file review summaries. Find ONLY cross-file "
        "issues that no single-file review could see:\n"
        "  - data-flow bugs between modules (e.g. mismatched function arg order across a call site)\n"
        "  - API inconsistency (modules returning different response shapes for the same kind of data)\n"
        "  - pattern-usage inconsistency (a pattern accepted in one file but flagged in another — "
        "decide the ONE correct call and list every file that must change)\n"
        'Return JSON: {"cross_file_findings": [{"rule": str, "severity": str, "files": [str], '
        '"message": str}]}'
    ),
    tools=[],
    model="sonnet",
    maxTurns=3,
)

COORDINATOR_SYSTEM = (
    "You run a multi-pass code review. NEVER review all files in a single pass — "
    "that dilutes attention and produces inconsistent depth. Spawn one file-reviewer "
    "subagent per file (parallel where possible), collect every structured summary, "
    "then pass the full set to the cross-file-integrator subagent. Combine both layers "
    "into the final report."
)


def _list_sources(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.ts") if p.is_file())


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=COORDINATOR_SYSTEM,
        allowed_tools=["Read", "Glob", "Grep", "Task", "Agent"],
        agents={"file-reviewer": FILE_REVIEWER, "cross-file-integrator": CROSS_FILE_INTEGRATOR},
        setting_sources=[],
        permission_mode="acceptEdits",
    )


async def single_pass_review(root: Path) -> str:
    files = _list_sources(root)
    blob = "\n\n".join(f"=== {p.relative_to(root)} ===\n{p.read_text()}" for p in files)
    options = ClaudeAgentOptions(setting_sources=[], allowed_tools=[])
    prompt = (
        f"Review ALL {len(files)} files below in one pass. Give per-file feedback with "
        f"bug count, severity, and specific line references for each.\n\n{blob}"
    )
    chunks = []
    async for message in query(prompt=prompt, options=options):
        chunks.append(str(message))
    return "\n".join(chunks)


async def multi_pass_review(root: Path) -> str:
    files = _list_sources(root)
    options = build_options()
    prompt = (
        f"Run a multi-pass review of the {len(files)} TypeScript files under {root}. "
        "One file-reviewer subagent per file, then the cross-file-integrator over all "
        "summaries. Produce a combined report and a single-pass-vs-multi-pass comparison."
    )
    chunks = []
    async for message in query(prompt=prompt, options=options):
        chunks.append(str(message))
    return "\n".join(chunks)


if __name__ == "__main__":
    root = Path(__file__).parent / "sample_project"
    print(asyncio.run(multi_pass_review(root)))
