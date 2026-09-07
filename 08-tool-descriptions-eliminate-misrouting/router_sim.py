"""A deterministic stand-in for how an LLM selects a tool from descriptions.

Premise (the exam's first point): the description is the primary signal for
tool selection. So we model selection as relevance between the query and each
tool's description:

  + shared meaningful words with the purpose            (weak signal)
  + a near-match to one of the description's examples    (strong signal)
  + a query hit on one of the tool's input-format signals (strong signal)
  boundary text ("Do NOT use for...") contributes nothing — it's a negative
    instruction, not a match target.

On a tie the FIRST tool wins — which is why, with v1's near-identical
descriptions, order queries that lack the word "order" fall through to
get_customer. That IS the misrouting.
"""

from __future__ import annotations

import re

from tool_specs import ToolSpec

_STOP = {
    "the", "a", "an", "of", "for", "to", "on", "in", "is", "my", "this", "me",
    "what", "who", "s", "all", "up", "did", "do", "does", "and", "or", "by",
    "show", "get", "pull", "look", "whats",
}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 1}


def relevance(query: str, spec: ToolSpec) -> float:
    q = _tokens(query)
    score = 0.0
    score += len(q & _tokens(spec.purpose)) * 1.0
    for ex in spec.examples:
        et = _tokens(ex)
        if et and len(q & et) / len(et) >= 0.5:
            score += 5.0
    for pat in spec.input_signals:
        if re.search(pat, query, re.I):
            score += 3.0
    return score


def select_tool(query: str, specs: list[ToolSpec]) -> tuple[str, dict[str, float]]:
    scores = {s.name: relevance(query, s) for s in specs}
    order = {s.name: i for i, s in enumerate(specs)}
    best = max(scores, key=lambda name: (scores[name], -order[name]))
    return best, scores
