"""Spoke agents. Each is ISOLATED: it has no shared memory, no inherited
context, and never talks to the other subagent. Everything it needs must be
in the prompt string the coordinator builds for it.

If a subagent returns weak results, the diagnostic is "did the coordinator
pass enough context?" — not "is the subagent broken?".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SubagentResult:
    subtopic: str
    source: str  # "web_search" | "document_analysis"
    content: str


WEB_SEARCH_SYSTEM = (
    "You are a WEB SEARCH subagent in a hub-and-spoke research system. "
    "You receive one fully-specified assignment from the coordinator and return "
    "concise, factual findings for exactly that assignment. You have no memory of "
    "other assignments and must rely solely on the context given in the prompt."
)

DOC_ANALYSIS_SYSTEM = (
    "You are a DOCUMENT ANALYSIS subagent in a hub-and-spoke research system. "
    "You extract and synthesise key points from reference material for exactly the "
    "assignment given. You have no memory of other assignments and must rely solely "
    "on the context given in the prompt."
)


def build_subagent_prompt(
    *,
    research_goal: str,
    topic: str,
    subtopic: str,
    prior_context: str,
    targeted_query: str | None = None,
) -> str:
    """Assemble the FULL context every isolated subagent needs."""
    lines = [
        f"RESEARCH GOAL: {research_goal}",
        f"OVERALL TOPIC: {topic}",
        f"YOUR ASSIGNED SUBTOPIC: {subtopic}",
        "",
        "CONTEXT FROM PRIOR AGENTS (you cannot see their raw work, only this summary):",
        prior_context or "  (none yet — you are among the first agents)",
        "",
    ]
    if targeted_query:
        lines += [
            "This is a REFINEMENT pass. The coordinator found the earlier result "
            f"insufficient. Focus specifically on: {targeted_query}",
            "",
        ]
    lines.append(
        f"Return 2-4 sentences of substantive findings on '{subtopic}' as it relates "
        f"to '{topic}'. Be specific (technologies, numbers, status)."
    )
    return "\n".join(lines)


def web_search_subagent(client, prompt: str, subtopic: str) -> SubagentResult:
    return SubagentResult(subtopic, "web_search", client.complete(WEB_SEARCH_SYSTEM, prompt))


def document_analysis_subagent(client, prompt: str, subtopic: str) -> SubagentResult:
    return SubagentResult(subtopic, "document_analysis", client.complete(DOC_ANALYSIS_SYSTEM, prompt))
