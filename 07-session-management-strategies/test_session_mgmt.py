"""Offline tests. Regenerates codebase/ each run so file edits are repeatable."""

from __future__ import annotations

from pathlib import Path

from analyzer import analyze_text
from compare import build_comparison, contradictions
from make_codebase import CHANGED_FILES, MODULES, apply_fixes, write
from session_strategies import fork, fresh_start_with_summary, resume_stale, start_initial_session

ROOT = Path(__file__).parent / "codebase"


def _fresh_codebase() -> Path:
    write(ROOT)
    return ROOT


def test_summary_is_conclusions_not_raw_tool_output():
    _fresh_codebase()
    _session, summary = start_initial_session(ROOT)
    block = summary.to_prompt_block()
    # no raw source lines carried through
    assert "console.log(" not in block and "export function" not in block
    # every issue has file, severity and a recommendation
    for i in summary.issues_flat():
        assert i.file and i.severity and i.recommendation
    assert len(block) < 2000
    print(f"summary: {len(summary.issues_flat())} issues, {len(block)} chars, no raw code")


def test_edits_change_analysis_results():
    _fresh_codebase()
    before = {n: analyze_text(n, t) for n, t, _ in
              [(rel.split('/')[-1], (ROOT / rel).read_text(), None) for rel, _ in MODULES]}
    apply_fixes(ROOT)
    for name in CHANGED_FILES:
        after = analyze_text(name, (ROOT / f"src/{name}").read_text())
        assert len(after) < len(before[name]), f"{name}: fix did not remove its issue"
    print(f"edits resolved the issue in each of {CHANGED_FILES}")


def test_stale_resume_gives_contradictory_advice():
    _fresh_codebase()
    session, _summary = start_initial_session(ROOT)
    apply_fixes(ROOT)
    advice = resume_stale(session)
    bad = contradictions(advice, ROOT)
    assert len(bad) == len(CHANGED_FILES), bad
    # specifically: it still tells you to fix the now-awaited promise
    assert any(a.file == "mod03.ts" and a.rule == "floating-promise" and a.action == "fix"
               for a in advice)
    print(f"stale resume: {len(bad)} contradictions (one per changed file)")


def test_fresh_start_is_consistent_and_targeted():
    _fresh_codebase()
    _session, summary = start_initial_session(ROOT)
    changed = apply_fixes(ROOT)
    result = fresh_start_with_summary(summary, ROOT, changed)
    assert contradictions(result.advice, ROOT) == []
    assert result.reanalyzed_files == sorted(changed)          # only the 3 changed files re-read
    assert set(result.carried_from_summary) == {
        f"mod{n:02d}.ts" for n in range(1, 11)
    } - set(changed)
    # the changed files are reported as resolved, not "still fix this"
    for name in changed:
        assert any(a.file == name and a.action == "resolved" for a in result.advice)
    print(f"fresh start: 0 contradictions, re-analysed only {result.reanalyzed_files}")


def test_fork_is_divergent_not_continuation():
    _fresh_codebase()
    session, _summary = start_initial_session(ROOT)
    branch = fork(session, "explore-alt-fix")
    # mutating the fork's snapshot must not touch the original session
    branch.snapshot["mod01.ts"] = "// experimental rewrite"
    assert session.snapshot["mod01.ts"] != "// experimental rewrite"
    assert branch.parent == session.name
    print("fork: independent snapshot copy, parent link preserved, original untouched")


def test_comparison_quality_gap():
    _fresh_codebase()
    c = build_comparison(ROOT)
    assert len(c.stale_contradictions) > 0
    assert len(c.fresh_contradictions) == 0
    assert len(c.stale_contradictions) > len(c.fresh_contradictions)
    print(c.render())


if __name__ == "__main__":
    test_summary_is_conclusions_not_raw_tool_output()
    test_edits_change_analysis_results()
    test_stale_resume_gives_contradictory_advice()
    test_fresh_start_is_consistent_and_targeted()
    test_fork_is_divergent_not_continuation()
    test_comparison_quality_gap()
    print("\nAll tests passed.")
