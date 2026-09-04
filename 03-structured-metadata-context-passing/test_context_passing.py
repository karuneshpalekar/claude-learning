"""Offline tests. No API key / SDK needed for these.

Run the live coordinator separately with:  python coordinator.py
(needs `pip install claude-agent-sdk` and the Claude Code CLI + a key).
"""

from __future__ import annotations

import asyncio

from findings import Finding, FindingSet, verify_attribution
from simulate import (
    gather_parallel,
    synthesize_preserving,
    synthesize_stripped,
)


def test_finding_separates_content_from_metadata():
    f = Finding(
        claim="X is true", analysis="with caveat",
        retrieved_by="document_analysis", document_name="d.pdf", page_number=3,
        confidence=0.9,
    )
    d = f.to_dict()
    assert {"claim", "analysis"} <= d.keys()                       # content
    assert {"source_url", "document_name", "page_number", "confidence", "retrieved_by"} <= d.keys()
    assert f.is_attributable()
    assert Finding(claim="orphan").is_attributable() is False
    print("Finding schema keeps content and attribution metadata as distinct fields")


def test_findingset_json_roundtrip_preserves_all_metadata():
    fs = FindingSet("t", [
        Finding(claim="a", retrieved_by="web_search", source_url="http://x", source_title="X", confidence=0.5),
        Finding(claim="b", retrieved_by="document_analysis", document_name="d.pdf", page_number=9, confidence=0.8),
    ])
    back = FindingSet.from_json(fs.to_json())
    assert back.findings[0].source_url == "http://x"
    assert back.findings[1].page_number == 9
    assert back.findings[1].confidence == 0.8
    print("FindingSet JSON round-trip loses no metadata (safe to pass to synthesis)")


def test_preserving_metadata_yields_full_attribution():
    fs = asyncio.run(gather_parallel(["cathode chemistry", "manufacturing"]))
    report = verify_attribution(synthesize_preserving(fs))
    assert report.complete, report.orphaned
    assert report.ratio == 1.0
    print(f"metadata preserved -> {report.attributed}/{report.total_claims} claims attributable")


def test_stripping_metadata_causes_attribution_failure():
    fs = asyncio.run(gather_parallel(["cathode chemistry", "manufacturing"]))
    report = verify_attribution(synthesize_stripped(fs))
    assert not report.complete
    assert len(report.orphaned) == len(fs.findings)
    print(f"metadata stripped -> {len(report.orphaned)} orphaned claims (coordinator fault)")


def test_parallel_faster_than_sequential():
    from simulate import gather_sequential
    import time

    subs = ["cathode chemistry", "manufacturing"]
    t = time.perf_counter(); asyncio.run(gather_sequential(subs)); seq = time.perf_counter() - t
    t = time.perf_counter(); asyncio.run(gather_parallel(subs)); par = time.perf_counter() - t
    assert par < seq / 2, f"parallel {par:.2f}s not much faster than sequential {seq:.2f}s"
    print(f"parallel spawn {par:.2f}s < sequential {seq:.2f}s")


def test_coordinator_allowedtools_gate():
    """The coordinator cannot spawn subagents unless 'Agent'/'Task' is allowed."""
    from coordinator import build_options
    opts = build_options()
    assert "Agent" in opts.allowed_tools or "Task" in opts.allowed_tools
    assert set(opts.agents) == {"web-search", "document-analysis", "synthesis"}
    assert opts.agents["synthesis"].tools == []          # no retrieval tools
    assert opts.agents["web-search"].tools == ["WebSearch", "WebFetch"]
    assert opts.agents["document-analysis"].tools == ["Read", "Grep", "Glob"]
    print("coordinator: Agent/Task in allowed_tools; subagents have scoped tool sets")


if __name__ == "__main__":
    test_finding_separates_content_from_metadata()
    test_findingset_json_roundtrip_preserves_all_metadata()
    test_preserving_metadata_yields_full_attribution()
    test_stripping_metadata_causes_attribution_failure()
    test_parallel_faster_than_sequential()
    try:
        test_coordinator_allowedtools_gate()
    except ModuleNotFoundError as e:
        print(f"skipped coordinator gate test (needs claude-agent-sdk): {e}")
    print("\nAll offline tests passed.")
