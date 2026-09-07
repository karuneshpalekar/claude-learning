"""Step 5: system-prompt conflicts.

A well-written description can still be overridden by a keyword-sensitive
instruction in the system prompt — "always check the customer's details first"
creates a standing pull toward get_customer no matter what the user asked.

`audit()` flags lines that combine an imperative ("always", "every", "first",
"must", "before anything") with a token that is strongly associated with one
tool, and proposes a routing-neutral rewrite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SYSTEM_PROMPT_V1 = """
You are a customer support agent.
- Always check the customer's account details before doing anything else.
- For every request, first look up the order history.
- Be concise and cite the record you used.
""".strip()

SYSTEM_PROMPT_V2 = """
You are a customer support agent.
- Select the tool whose description matches what the user actually asked for.
- Call a tool only when the user's request needs that specific data; do not
  pre-fetch customer or order records by default.
- Be concise and cite the record you used.
""".strip()

_IMPERATIVES = ("always", "every", "first", "must", "before anything", "before doing anything")
_TOOL_KEYWORDS = {
    "get_customer": ("customer", "account", "buyer", "profile", "contact"),
    "lookup_order": ("order", "purchase", "shipment", "delivery", "transaction", "refund"),
}


@dataclass
class Conflict:
    line: str
    imperative: str
    pulls_toward: str
    why: str
    rewrite: str


def audit(system_prompt: str) -> list[Conflict]:
    conflicts: list[Conflict] = []
    for raw in system_prompt.splitlines():
        line = raw.strip(" -\t")
        low = line.lower()
        imp = next((k for k in _IMPERATIVES if k in low), None)
        if not imp:
            continue
        for tool, kws in _TOOL_KEYWORDS.items():
            if any(re.search(rf"\b{kw}", low) for kw in kws):
                conflicts.append(Conflict(
                    line=line,
                    imperative=imp,
                    pulls_toward=tool,
                    why=(
                        f"'{imp}' + '{next(k for k in kws if k in low)}' makes {tool} a default "
                        "action, overriding per-request tool selection from the descriptions."
                    ),
                    rewrite=(
                        "Call a tool only when the user's request needs that specific data; "
                        "choose it from the tool descriptions, not from a standing rule."
                    ),
                ))
                break
    return conflicts


if __name__ == "__main__":
    for c in audit(SYSTEM_PROMPT_V1):
        print(f"CONFLICT: {c.line!r}\n  pulls toward: {c.pulls_toward}\n  why: {c.why}\n  rewrite: {c.rewrite}\n")
