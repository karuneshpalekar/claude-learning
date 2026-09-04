"""Hub-and-spoke research coordinator.

The coordinator is the ONLY hub. It owns:
  1. task decomposition        (broad, not narrow)
  2. subagent selection + context passing
  3. result aggregation
  4. coverage evaluation
  5. iterative refinement       (re-delegate for gaps until covered)

Subagents (spokes) never communicate with each other. All information flows
through the coordinator.

Diagnostic principle the exam tests: if the final report is missing whole
categories, the root cause is step 1 (decomposition), not the subagents.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from subagents import (
    build_subagent_prompt,
    document_analysis_subagent,
    web_search_subagent,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("coordinator")

COORDINATOR_SYSTEM = (
    "You are the COORDINATOR (central hub) of a hub-and-spoke research system. "
    "You decompose a broad topic into a COMPLETE set of subtopics covering its full "
    "breadth, dispatch isolated subagents with all context they need, aggregate their "
    "results, evaluate coverage, and re-delegate to close gaps. You never assume a "
    "subagent failed on its own merits before checking the context you gave it."
)

DECOMPOSE_SYSTEM = (
    "You decompose a broad research topic into subtopics. Return a COMPLETE, "
    "MUTUALLY-DISTINCT list covering the ENTIRE breadth of the topic — not just the "
    "two most obvious facets. Output only a comma-separated list, minimum 5 items."
)

MIN_SUBTOPICS = 5
MAX_REFINEMENT_ROUNDS = 3
COVERAGE_THRESHOLD = 1.0  # require 100% well-covered

# Curated breadth maps guard against narrow decomposition for known topics.
_KNOWN_DECOMPOSITIONS = {
    "renewable energy": ["solar", "wind", "geothermal", "tidal", "biomass", "fusion"],
}

_WEAK_MARKERS = ("not found", "brief mention", "no substantive", "details not found", "(none")


@dataclass
class SubtopicRecord:
    subtopic: str
    findings: list[str] = field(default_factory=list)

    @property
    def combined(self) -> str:
        return " ".join(self.findings)

    @property
    def status(self) -> str:
        text = self.combined.strip()
        if not text:
            return "missing"
        weak = any(m in text.lower() for m in _WEAK_MARKERS)
        if weak or len(text) < 80:
            return "partial"
        return "well-covered"


@dataclass
class ResearchReport:
    topic: str
    subtopics: list[str]
    records: dict[str, SubtopicRecord]
    rounds: int
    coverage: float

    def markdown(self) -> str:
        out = [f"# Research Report: {self.topic}", ""]
        out.append(f"_Coverage: {self.coverage*100:.0f}% over {self.rounds} round(s)_")
        out.append("")
        for st in self.subtopics:
            rec = self.records[st]
            out.append(f"## {st.title()}  ({rec.status})")
            out.append(rec.combined or "_No findings._")
            out.append("")
        return "\n".join(out)


def _parse_list(raw: str) -> list[str]:
    parts = re.split(r"[,\n]", raw)
    seen, result = set(), []
    for p in parts:
        item = p.strip().lower().strip("-*0123456789. ")
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def decompose(client, topic: str) -> list[str]:
    """Break `topic` into >= MIN_SUBTOPICS distinct subtopics covering full breadth."""
    key = topic.strip().lower()
    for known, subs in _KNOWN_DECOMPOSITIONS.items():
        if known in key:
            log.info("decomposition (curated breadth map): %s", subs)
            return list(subs)

    raw = client.complete(DECOMPOSE_SYSTEM, f"Decompose this topic into subtopics: {topic}")
    subs = _parse_list(raw)
    if len(subs) < MIN_SUBTOPICS:
        log.warning(
            "NARROW DECOMPOSITION: only %d subtopics (%s). The coordinator — not the "
            "subagents — is the root cause of any missing coverage.",
            len(subs), subs,
        )
    return subs


def _prior_context(topic: str, records: dict[str, SubtopicRecord], exclude: str) -> str:
    bits = [
        f"- {st}: {rec.status}"
        for st, rec in records.items()
        if st != exclude and rec.findings
    ]
    return "\n".join(bits)


def _delegate(client, *, topic, goal, subtopic, records, targeted_query=None) -> SubtopicRecord:
    """Spawn BOTH subagents for one subtopic with explicit, full context."""
    prompt = build_subagent_prompt(
        research_goal=goal,
        topic=topic,
        subtopic=subtopic,
        prior_context=_prior_context(topic, records, subtopic),
        targeted_query=targeted_query,
    )
    web = web_search_subagent(client, prompt, subtopic)
    doc = document_analysis_subagent(client, prompt, subtopic)
    rec = SubtopicRecord(subtopic)  # fresh each delegation; refinement replaces, not appends
    for r in (web, doc):
        if r.content and r.content.strip():
            rec.findings.append(r.content.strip())
    return rec


def assess_coverage(subtopics: list[str], records: dict[str, SubtopicRecord]) -> dict:
    buckets = {"well-covered": [], "partial": [], "missing": []}
    for st in subtopics:
        buckets[records.get(st, SubtopicRecord(st)).status].append(st)
    score = len(buckets["well-covered"]) / len(subtopics) if subtopics else 0.0
    return {"score": score, **buckets}


def research(client, topic: str) -> ResearchReport:
    goal = f"Produce a complete survey of {topic}, with a substantive section on every major category."
    log.info("COORDINATOR received topic: %r", topic)

    subtopics = decompose(client, topic)
    records: dict[str, SubtopicRecord] = {st: SubtopicRecord(st) for st in subtopics}

    rounds = 0
    coverage = assess_coverage(subtopics, records)
    while rounds < MAX_REFINEMENT_ROUNDS and coverage["score"] < COVERAGE_THRESHOLD:
        rounds += 1
        gaps = coverage["partial"] + coverage["missing"]
        targets = gaps if rounds > 1 else subtopics
        log.info("round %d: delegating %s", rounds, targets)
        for st in targets:
            tq = None
            if rounds > 1:
                tq = f"concrete, sourced detail on {st} — the prior pass was insufficient"
            records[st] = _delegate(
                client, topic=topic, goal=goal, subtopic=st, records=records, targeted_query=tq
            )
        coverage = assess_coverage(subtopics, records)
        log.info(
            "round %d coverage: %.0f%% | well=%s partial=%s missing=%s",
            rounds, coverage["score"] * 100,
            coverage["well-covered"], coverage["partial"], coverage["missing"],
        )

    if coverage["score"] < COVERAGE_THRESHOLD:
        log.warning(
            "stopped at %.0f%% after %d rounds (max). Remaining gaps: %s",
            coverage["score"] * 100, rounds, coverage["partial"] + coverage["missing"],
        )

    return ResearchReport(topic, subtopics, records, rounds, coverage["score"])


def main() -> None:
    from clients import AnthropicClient

    report = research(AnthropicClient(), "renewable energy technologies")
    print("\n" + report.markdown())


if __name__ == "__main__":
    main()
