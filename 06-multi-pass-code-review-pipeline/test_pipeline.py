"""Offline tests — run make_sample_project first if sample_project/ is absent."""

from __future__ import annotations

from pathlib import Path

from analyzers import analyze_project, cross_file_analysis, review_per_file, review_single_pass
from compare import build_comparison
from make_sample_project import write as write_sample

ROOT = Path(__file__).parent / "sample_project"
if not (ROOT / "src" / "index.ts").exists():
    write_sample(ROOT)


def test_project_has_at_least_10_files():
    analyzed = analyze_project(ROOT)
    assert len(analyzed) >= 10
    print(f"sample project: {len(analyzed)} source files")


def test_single_pass_shows_attention_dilution():
    c = build_comparison(ROOT)
    # later files get less attention than earlier files
    assert c.second_half_single < c.first_half_single, (
        f"expected drop-off, got first={c.first_half_single} second={c.second_half_single}"
    )
    print(f"single-pass drop-off: first half {c.first_half_single} issues, "
          f"second half {c.second_half_single}")


def test_per_file_pass_is_consistent_depth():
    analyzed = analyze_project(ROOT)
    per_file = review_per_file(analyzed)
    for name, _text, findings in analyzed:
        assert len(per_file[name]) == len(findings), f"{name}: per-file pass dropped findings"
    # the LAST file with issues is reported as fully as the first
    with_issues = [(n, f) for n, _t, f in analyzed if f]
    first_name, first_f = with_issues[0]
    last_name, last_f = with_issues[-1]
    assert len(per_file[last_name]) == len(last_f) and len(per_file[first_name]) == len(first_f)
    print(f"per-file pass: {first_name} and {last_name} both fully reported")


def test_multi_pass_finds_more_total_issues():
    c = build_comparison(ROOT)
    assert c.multi_total > c.single_total
    print(f"total issues: single-pass {c.single_total}  ->  multi-pass {c.multi_total}")


def test_cross_file_pass_finds_issues_no_per_file_pass_could():
    cross = [f for f in cross_file_analysis(analyze_project(ROOT)) if not f.rule.startswith("recurring:")]
    rules = {f.rule for f in cross}
    assert {"api-shape-inconsistency", "arg-order-mismatch"} <= rules, rules
    assert len(cross) >= 3
    print(f"cross-file pass found: {sorted(rules)}")


def test_dilution_artefact_forEach_flagged_then_approved():
    c = build_comparison(ROOT)
    by_rule = {a.rule: a for a in c.artefacts}
    assert "foreach-async" in by_rule, "the canonical forEach artefact must appear"
    a = by_rule["foreach-async"]
    assert "array.ts" in a.flagged_in and "collection.ts" in a.missed_in
    # and the multi-pass (per-file) treats both identically
    per_file = review_per_file(analyze_project(ROOT))
    assert any(f.rule == "foreach-async" for f in per_file["array.ts"])
    assert any(f.rule == "foreach-async" for f in per_file["collection.ts"])
    print("artefact: forEach(async) flagged in array.ts, approved in collection.ts by single-pass; "
          "multi-pass flags both")


if __name__ == "__main__":
    test_project_has_at_least_10_files()
    test_single_pass_shows_attention_dilution()
    test_per_file_pass_is_consistent_depth()
    test_multi_pass_finds_more_total_issues()
    test_cross_file_pass_finds_issues_no_per_file_pass_could()
    test_dilution_artefact_forEach_flagged_then_approved()
    print("\nAll tests passed.")
