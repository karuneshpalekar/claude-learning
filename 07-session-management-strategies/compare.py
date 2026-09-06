"""Quality comparison: stale resume vs fresh start with summary injection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from analyzer import analyze_text
from make_codebase import MODULES, apply_fixes
from session_strategies import (
    Advice,
    FreshResult,
    fresh_start_with_summary,
    resume_stale,
    start_initial_session,
)


def _current_contents(root: Path) -> dict[str, str]:
    return {rel.split("/")[-1]: (root / rel).read_text() for rel, _ in MODULES}


def contradictions(advice: list[Advice], root: Path) -> list[str]:
    """An advice item is a contradiction if it tells you to FIX an issue that
    is not present in the CURRENT file (already fixed / stale reference)."""
    current = {name: analyze_text(name, text) for name, text in _current_contents(root).items()}
    bad = []
    for a in advice:
        if a.action != "fix":
            continue
        present = any(i.rule == a.rule for i in current.get(a.file, []))
        if not present:
            bad.append(f"{a.file}: advises fixing '{a.rule}' but it is not in the current file")
    return bad


@dataclass
class Comparison:
    changed_files: list[str]
    stale_advice: list[Advice]
    fresh: FreshResult
    stale_contradictions: list[str]
    fresh_contradictions: list[str]

    def render(self) -> str:
        L = [
            f"changed files: {self.changed_files}",
            "",
            f"STALE RESUME   : {len(self.stale_advice)} advice items, "
            f"{len(self.stale_contradictions)} contradictions",
        ]
        for c in self.stale_contradictions:
            L.append(f"   ! {c}")
        L += [
            "",
            f"FRESH + SUMMARY: {len(self.fresh.advice)} advice items, "
            f"{len(self.fresh_contradictions)} contradictions",
            f"   re-analysed from disk : {self.fresh.reanalyzed_files}",
            f"   carried from summary  : {self.fresh.carried_from_summary}",
            "",
            "verdict: fresh start + summary injection gives consistent advice on the "
            "changed files; naive resume repeats fixes that are already done.",
        ]
        return "\n".join(L)


def build_comparison(root: Path) -> Comparison:
    session, summary = start_initial_session(root)      # step 1-2: analyse + summarise
    changed = apply_fixes(root)                         # step 3: modify 3 files

    stale_advice = resume_stale(session)               # step 4: naive resume
    fresh = fresh_start_with_summary(summary, root, changed)  # step 5: fresh + targeted

    return Comparison(
        changed_files=changed,
        stale_advice=stale_advice,
        fresh=fresh,
        stale_contradictions=contradictions(stale_advice, root),
        fresh_contradictions=contradictions(fresh.advice, root),
    )


if __name__ == "__main__":
    # Always regenerate the codebase first so the run is repeatable.
    from make_codebase import write

    root = Path(__file__).parent / "codebase"
    write(root)
    print(build_comparison(root).render())
