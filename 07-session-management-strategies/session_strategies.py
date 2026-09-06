"""The three session-management strategies, modelled deterministically.

A "session" here is a name + the frozen file contents it captured as tool
results the first time it read them. That frozen snapshot is exactly what
goes stale when the real files change on disk.

  resume                  -> reason from the frozen snapshot (stale after edits)
  fork_session            -> copy the snapshot into a new branch; the original
                             is untouched (divergent exploration)
  fresh start + summary   -> discard the snapshot, keep the structured summary,
                             re-read ONLY the changed files (targeted)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from analyzer import AnalysisSummary, Issue, analyze_project, analyze_text
from make_codebase import MODULES


@dataclass
class Session:
    name: str
    snapshot: dict[str, str]              # file -> contents at capture time
    parent: str | None = None


@dataclass
class Advice:
    file: str
    action: str                          # "fix" | "resolved" | "clean"
    rule: str
    detail: str
    source: str                          # "stale-snapshot" | "current-file" | "summary"


def start_initial_session(root: Path, name: str = "codebase-review-v1"):
    analyzed = analyze_project(root)
    snapshot = {n: t for n, t, _ in analyzed}
    summary = AnalysisSummary.from_analysis(name, analyzed)
    return Session(name, snapshot), summary


# --- the advisor: turn file contents (+ optional prior knowledge) into advice

def _advise_over_contents(contents: dict[str, str], *, source: str,
                          prior: AnalysisSummary | None = None) -> list[Advice]:
    advice: list[Advice] = []
    prior_by_file: dict[str, list[Issue]] = {}
    if prior:
        for ff in prior.findings:
            prior_by_file[ff.file] = ff.issues

    for name, text in contents.items():
        current = analyze_text(name, text)
        current_keys = {(i.rule, i.line) for i in current}
        for i in current:
            advice.append(Advice(name, "fix", i.rule, i.recommendation, source))
        # If we have prior knowledge, note issues that are now gone as resolved.
        for old in prior_by_file.get(name, []):
            if (old.rule, old.line) not in current_keys and old.rule not in {a.rule for a in current}:
                advice.append(Advice(name, "resolved", old.rule,
                                     f"previously flagged {old.rule} is no longer present", "summary"))
        if not current and name not in prior_by_file:
            advice.append(Advice(name, "clean", "-", "no issues", source))
    return advice


# --- strategy 1: naive resume (stale) ------------------------------------

def resume_stale(session: Session) -> list[Advice]:
    """Re-review using the session's OLD tool-result snapshot. After the files
    changed on disk, this advises fixing issues that are already fixed and
    references code that no longer exists."""
    return _advise_over_contents(session.snapshot, source="stale-snapshot")


# --- strategy 2: fork_session ------------------------------------------

def fork(session: Session, new_name: str | None = None) -> Session:
    """Branch for divergent exploration. The fork gets its OWN copy of the
    snapshot; mutating it never affects the original session."""
    return Session(
        name=new_name or f"{session.name} (fork)",
        snapshot=dict(session.snapshot),
        parent=session.name,
    )


# --- strategy 3: fresh start with summary injection + targeted re-analysis

@dataclass
class FreshResult:
    advice: list[Advice]
    reanalyzed_files: list[str]
    carried_from_summary: list[str]


def fresh_start_with_summary(summary: AnalysisSummary, root: Path,
                             changed_files: list[str]) -> FreshResult:
    """No stale tool results. Keep the structured summary for everything, and
    re-read from disk ONLY the files that changed."""
    changed = set(changed_files)
    current_contents = {
        rel.split("/")[-1]: (root / rel).read_text()
        for rel, _ in MODULES
        if rel.split("/")[-1] in changed
    }
    advice = _advise_over_contents(current_contents, source="current-file", prior=summary)

    # Unchanged files: knowledge comes straight from the summary, no re-read.
    carried = []
    for ff in summary.findings:
        if ff.file in changed:
            continue
        carried.append(ff.file)
        for i in ff.issues:
            advice.append(Advice(ff.file, "fix", i.rule, i.recommendation, "summary"))
    return FreshResult(advice, sorted(changed), sorted(carried))
