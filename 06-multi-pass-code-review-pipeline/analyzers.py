"""Deterministic light-weight static checks + the single-pass / multi-pass
simulations.

The point isn't to be a real linter — it's to have a *reproducible* reviewer
so the attention-dilution phenomenon can be shown structurally:

- The underlying issues are real and several patterns recur across files.
- `review_single_pass` applies a shrinking attention budget by file position:
  early files get every finding, later files get one or none. That is the
  dilution artefact — the SAME pattern is reported in an early file and
  silently dropped in a late one.
- `review_multi_pass` gives every file the full budget (per-file pass), then
  runs a separate `cross_file_analysis` that no per-file pass could produce.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from make_sample_project import FILES as SAMPLE_FILE_ORDER


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule: str
    severity: str  # "low" | "medium" | "high"
    message: str


_CHECKS = [
    ("loose-equality", re.compile(r"\s[=!]=\s(?!=)"), "medium", "use strict === / !=="),
    ("foreach-async", re.compile(r"\.forEach\(\s*async\b"), "medium",
     "forEach with an async callback does not await; use for...of"),
    ("debug-logging", re.compile(r"\bconsole\.log\("), "low", "remove debug logging"),
    ("any-type", re.compile(r":\s*any\b"), "low", "avoid `any`; give a real type"),
    ("floating-promise", re.compile(r"^\s*[A-Za-z_][\w.]*\.(save|flush|commit|persist)\("), "high",
     "promise result is neither awaited nor returned"),
    ("todo", re.compile(r"//\s*TODO"), "low", "unresolved TODO"),
]


def analyze_text(file_name: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule, pat, sev, msg in _CHECKS:
            if pat.search(line):
                findings.append(Finding(file_name, lineno, rule, sev, msg))
    return findings


def analyze_project(root: Path) -> list[tuple[str, str, list[Finding]]]:
    """Returns [(file_name, text, findings)] in the FIXED sample order so the
    single-pass position simulation is reproducible."""
    out = []
    for rel, _ in SAMPLE_FILE_ORDER:
        name = rel.split("/")[-1]
        text = (root / rel).read_text()
        out.append((name, text, analyze_text(name, text)))
    return out


# --- single pass: attention dilution by file position --------------------

def review_single_pass(analyzed: list[tuple[str, str, list[Finding]]]) -> dict[str, list[Finding]]:
    n = len(analyzed)
    reported: dict[str, list[Finding]] = {}
    for i, (name, _text, findings) in enumerate(analyzed):
        frac = i / n
        if frac < 0.30:                       # early: full attention
            kept = list(findings)
        elif frac < 0.65:                     # middle: only the worst survives
            high = [f for f in findings if f.severity == "high"]
            kept = high or findings[:1]
        else:                                 # late: attention spent
            kept = findings[:1] if i % 3 == 0 else []
        reported[name] = kept
    return reported


# --- multi pass: per-file (full budget) + cross-file integration ---------

def review_per_file(analyzed: list[tuple[str, str, list[Finding]]]) -> dict[str, list[Finding]]:
    return {name: list(findings) for name, _text, findings in analyzed}


def cross_file_analysis(analyzed: list[tuple[str, str, list[Finding]]]) -> list[Finding]:
    by_name = {name: text for name, text, _ in analyzed}
    cross: list[Finding] = []

    # 1. API response-shape drift across api/ modules.
    shapes = {}
    for name, text in by_name.items():
        if name in {"users.ts", "orders.ts", "inventory.ts"}:
            if re.search(r"return\s*\{\s*data\s*:", text):
                shapes[name] = "envelope {data: ...}"
            elif re.search(r"return\s+\w+\s*;", text) or re.search(r"return\s+DB\s*;", text):
                shapes[name] = "bare value/array"
    if len(set(shapes.values())) > 1:
        cross.append(Finding(
            "+".join(sorted(shapes)), 0, "api-shape-inconsistency", "high",
            f"API modules disagree on response shape: {shapes}",
        ))

    # 2. formatMoney argument-order mismatch (data-flow bug across files).
    m = re.search(r"function formatMoney\((\w+):\s*number,\s*(\w+):", by_name.get("format.ts", ""))
    if m:
        p0, p1 = m.group(1), m.group(2)
        for name, text in by_name.items():
            call = re.search(r"formatMoney\((\w+),\s*(\w+)\)", text)
            if call and (call.group(1) == p1 or "currency" in call.group(1).lower()):
                cross.append(Finding(
                    f"{name}->format.ts", 0, "arg-order-mismatch", "high",
                    f"formatMoney expects ({p0}, {p1}) but {name} passes "
                    f"({call.group(1)}, {call.group(2)})",
                ))

    # 3. Config-key drift.
    keys = set()
    for text in by_name.values():
        keys.update(re.findall(r"\bMAX_RETR[A-Z_]*\b", text))
    if len(keys) > 1:
        cross.append(Finding(
            "paymentService.ts+retryService.ts", 0, "config-key-drift", "medium",
            f"same concept under different names: {sorted(keys)}",
        ))

    # 4. Recurring local pattern -> must be handled uniformly project-wide.
    rule_files: dict[str, set[str]] = {}
    for name, _text, findings in analyzed:
        for f in findings:
            rule_files.setdefault(f.rule, set()).add(name)
    for rule, files in sorted(rule_files.items()):
        if len(files) >= 2:
            cross.append(Finding(
                "+".join(sorted(files)), 0, f"recurring:{rule}", "low",
                f"'{rule}' appears in {len(files)} files — apply one consistent decision",
            ))

    return cross
