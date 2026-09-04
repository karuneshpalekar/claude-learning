"""Structured findings: content fields kept SEPARATE from attribution metadata.

The exam's attribution-failure pattern: a synthesis agent emits unsourced
claims. Root cause is *not* the synthesis prompt — it is the coordinator
passing bare claim text instead of the full structured record. The fix is a
type where every claim travels with its metadata.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

Source = Literal["web_search", "document_analysis"]


@dataclass
class Finding:
    # --- content ---------------------------------------------------------
    claim: str                      # the factual assertion
    analysis: str = ""              # interpretation / caveats (doc agent fills this)

    # --- attribution metadata (kept separate from content) --------------
    retrieved_by: Source = "web_search"
    source_url: Optional[str] = None          # web_search findings
    source_title: Optional[str] = None        # web_search findings
    document_name: Optional[str] = None       # document_analysis findings
    page_number: Optional[int] = None         # document_analysis findings
    confidence: float = 0.0                   # 0.0-1.0, set by the retrieving agent

    def is_attributable(self) -> bool:
        """A finding can be cited iff it carries a resolvable source."""
        if self.source_url:
            return True
        return bool(self.document_name and self.page_number is not None)

    def citation(self) -> str:
        if self.source_url:
            title = self.source_title or self.source_url
            return f"[{title}]({self.source_url})"
        if self.document_name and self.page_number is not None:
            return f"[{self.document_name}, p.{self.page_number}]"
        return "[UNATTRIBUTED]"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FindingSet:
    """What the coordinator passes to the synthesis agent — COMPLETE, no fields
    stripped or summarised away."""

    topic: str
    findings: list[Finding] = field(default_factory=list)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            {"topic": self.topic, "findings": [f.to_dict() for f in self.findings]},
            indent=indent,
        )

    @staticmethod
    def from_json(raw: str) -> "FindingSet":
        data = json.loads(raw)
        return FindingSet(
            topic=data["topic"],
            findings=[Finding(**f) for f in data["findings"]],
        )


# --- verification ---------------------------------------------------------

@dataclass
class AttributionReport:
    total_claims: int
    attributed: int
    orphaned: list[str]

    @property
    def complete(self) -> bool:
        return self.total_claims > 0 and not self.orphaned

    @property
    def ratio(self) -> float:
        return self.attributed / self.total_claims if self.total_claims else 0.0


def verify_attribution(synthesis_claims: list[dict]) -> AttributionReport:
    """Check that every claim in the synthesis output carries a source URL or a
    document name + page number.

    `synthesis_claims` is the structured output of the synthesis agent:
    a list of {"text": str, "source_url": str|None, "document_name": str|None,
    "page_number": int|None}.
    """
    orphaned: list[str] = []
    attributed = 0
    for c in synthesis_claims:
        has_url = bool(c.get("source_url"))
        has_page = bool(c.get("document_name") and c.get("page_number") is not None)
        if has_url or has_page:
            attributed += 1
        else:
            orphaned.append(c.get("text", "<no text>"))
    return AttributionReport(len(synthesis_claims), attributed, orphaned)
