"""Structured handoff protocol.

Human agents who pick up an escalation do NOT see the conversation transcript
— the handoff object IS everything they get. It must be self-contained: five
required fields, none empty, none a placeholder ("TBD", "N/A", "...").
"""

from __future__ import annotations

from dataclasses import dataclass

_PLACEHOLDER_MARKERS = {"tbd", "n/a", "na", "...", "unknown", "todo", "placeholder", ""}


@dataclass
class Handoff:
    customer_id: str
    summary: str               # self-contained recap — no "see above"
    root_cause: str
    amount: float
    recommended_action: str

    def validate(self) -> list[str]:
        problems = []
        for field_name in ("customer_id", "summary", "root_cause", "recommended_action"):
            val = str(getattr(self, field_name)).strip().lower()
            if val in _PLACEHOLDER_MARKERS:
                problems.append(f"{field_name} is empty or a placeholder")
        if self.amount < 0:
            problems.append("amount is negative")
        return problems

    def is_complete(self) -> bool:
        return not self.validate()

    def render(self) -> str:
        return (
            f"HANDOFF — customer_id={self.customer_id}\n"
            f"Amount in dispute: ${self.amount:.2f}\n"
            f"Summary: {self.summary}\n"
            f"Root cause: {self.root_cause}\n"
            f"Recommended action: {self.recommended_action}\n"
        )


def compile_handoff(
    *, customer_id: str, summary: str, root_cause: str, amount: float, recommended_action: str
) -> Handoff:
    h = Handoff(customer_id, summary, root_cause, amount, recommended_action)
    problems = h.validate()
    if problems:
        raise ValueError(f"incomplete handoff: {problems}")
    return h
