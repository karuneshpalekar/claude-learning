"""Deterministic checks + the structured analysis summary."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from make_codebase import MODULES

_CHECKS = [
    ("loose-equality", re.compile(r"\s[=!]=\s(?!=)"), "medium", "use strict === / !=="),
    ("any-type", re.compile(r":\s*any\b"), "low", "replace `any` with a concrete type"),
    ("floating-promise", re.compile(r"^\s*[A-Za-z_][\w.]*\.(save|emit|flush)\((?!.*await)"), "high",
     "await the promise or return it"),
    ("debug-logging", re.compile(r"\bconsole\.log\("), "low", "remove debug logging"),
    ("unguarded-access", re.compile(r"\breturn\s+\w+\.\w+\.\w+;"), "high",
     "guard the optional property access (?. / null check)"),
]


@dataclass(frozen=True)
class Issue:
    file: str
    line: int
    rule: str
    severity: str
    recommendation: str


def analyze_text(name: str, text: str) -> list[Issue]:
    out: list[Issue] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if "await " in line:  # skip already-awaited lines for the floating-promise check
            floating_ok = True
        else:
            floating_ok = False
        for rule, pat, sev, rec in _CHECKS:
            if rule == "floating-promise" and floating_ok:
                continue
            if pat.search(line):
                out.append(Issue(name, lineno, rule, sev, rec))
    return out


def analyze_project(root: Path) -> list[tuple[str, str, list[Issue]]]:
    result = []
    for rel, _ in MODULES:
        name = rel.split("/")[-1]
        text = (root / rel).read_text()
        result.append((name, text, analyze_text(name, text)))
    return result


# --- structured summary (injected into a fresh session) -------------------

@dataclass
class FileFinding:
    file: str
    issues: list[Issue] = field(default_factory=list)


@dataclass
class AnalysisSummary:
    session_name: str
    findings: list[FileFinding]

    @classmethod
    def from_analysis(cls, session_name: str, analyzed) -> "AnalysisSummary":
        return cls(session_name, [FileFinding(n, list(iss)) for n, _t, iss in analyzed])

    def issues_flat(self) -> list[Issue]:
        return [i for ff in self.findings for i in ff.issues]

    def to_prompt_block(self) -> str:
        """Concise, conclusions only — NO raw file contents / tool output."""
        lines = [f"PRIOR ANALYSIS SUMMARY (session: {self.session_name})"]
        for ff in self.findings:
            if not ff.issues:
                lines.append(f"- {ff.file}: clean")
                continue
            for i in ff.issues:
                lines.append(f"- {ff.file}:{i.line} [{i.severity}] {i.rule} -> {i.recommendation}")
        return "\n".join(lines)
