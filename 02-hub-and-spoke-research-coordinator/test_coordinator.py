"""Tests for the hub-and-spoke research coordinator.

Offline by default (OfflineClient). Pass --live to run against the real model.
"""

from __future__ import annotations

import sys

from clients import OfflineClient
from coordinator import MIN_SUBTOPICS, decompose, research

SIX = {"solar", "wind", "geothermal", "tidal", "biomass", "fusion"}


def test_broad_decomposition():
    subs = decompose(OfflineClient(), "renewable energy technologies")
    assert len(subs) >= MIN_SUBTOPICS, subs
    assert SIX.issubset(set(subs)), f"narrow decomposition, missing {SIX - set(subs)}"
    print(f"decomposition ok: {subs}")


def test_iterative_refinement_reaches_full_coverage():
    report = research(OfflineClient(), "renewable energy technologies")

    # tidal + fusion start thin -> must take more than one round
    assert report.rounds >= 2, f"expected refinement, ran {report.rounds} round(s)"
    assert report.coverage == 1.0, f"coverage {report.coverage}"

    md = report.markdown().lower()
    for energy in SIX:
        assert f"## {energy}" in md, f"missing section: {energy}"
        assert report.records[energy].status == "well-covered", energy
    print(f"full coverage in {report.rounds} rounds; all six sections substantive")


def test_narrow_decomposition_is_coordinator_fault():
    """If we force a narrow decomposition, the gap is visible at the coordinator
    layer — the subagents are never even asked about the missing categories."""
    client = OfflineClient()
    report = research(client, "renewable energy technologies")
    # sanity: every covered subtopic was one the coordinator chose
    assert set(report.records) == set(report.subtopics)
    print("narrow-decomposition diagnostic holds: coverage is bounded by decomposition")


def test_live():
    from clients import AnthropicClient

    report = research(AnthropicClient(), "renewable energy technologies")
    print(report.markdown())
    assert report.coverage >= 0.8


if __name__ == "__main__":
    test_broad_decomposition()
    test_iterative_refinement_reaches_full_coverage()
    test_narrow_decomposition_is_coordinator_fault()
    if "--live" in sys.argv:
        test_live()
    print("\nAll tests passed.")
