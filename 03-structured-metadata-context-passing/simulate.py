"""Offline simulation of the context-passing pipeline — no API key, no SDK.

Demonstrates the exam's attribution-failure pattern directly:
  - synthesize_preserving()  passes the FULL Finding records  -> 100% attributable
  - synthesize_stripped()    passes only claim text           -> orphaned claims

Also times sequential vs parallel subagent spawning.
"""

from __future__ import annotations

import asyncio
import time

from findings import Finding, FindingSet, verify_attribution

# --- fake subagents (each returns STRUCTURED findings) --------------------

_WEB = {
    "cathode chemistry": Finding(
        claim="Sulfide solid electrolytes reach ionic conductivities above 10 mS/cm at room temperature.",
        retrieved_by="web_search",
        source_url="https://example.org/solid-state-review",
        source_title="Solid-State Battery Review 2025",
        confidence=0.82,
    ),
    "manufacturing": Finding(
        claim="Dry-electrode coating removes the solvent-recovery step, cutting cell-line energy use ~30%.",
        retrieved_by="web_search",
        source_url="https://example.org/dry-electrode",
        source_title="Dry Electrode Manufacturing",
        confidence=0.7,
    ),
}

_DOC = {
    "cathode chemistry": Finding(
        claim="Lithium dendrite penetration through the electrolyte remains the main cycle-life limiter.",
        analysis="The cited study stops at 300 cycles; automotive targets are ~1500.",
        retrieved_by="document_analysis",
        document_name="ssb_teardown_report.pdf",
        page_number=14,
        confidence=0.9,
    ),
    "manufacturing": Finding(
        claim="Stack pressure of 1-5 MPa must be maintained mechanically over pack life.",
        analysis="Adds pack mass; trade-off not quantified in the source.",
        retrieved_by="document_analysis",
        document_name="ssb_teardown_report.pdf",
        page_number=22,
        confidence=0.85,
    ),
}


async def _web_search_subagent(subtopic: str) -> Finding:
    await asyncio.sleep(0.3)  # simulate latency
    return _WEB[subtopic]


async def _document_analysis_subagent(subtopic: str) -> Finding:
    await asyncio.sleep(0.3)
    return _DOC[subtopic]


# --- coordinator delegation patterns ------------------------------------

async def gather_sequential(subtopics: list[str]) -> FindingSet:
    fs = FindingSet(topic="solid-state batteries")
    for st in subtopics:
        fs.findings.append(await _web_search_subagent(st))
        fs.findings.append(await _document_analysis_subagent(st))
    return fs


async def gather_parallel(subtopics: list[str]) -> FindingSet:
    """Independent subagents spawned together — the correct pattern."""
    tasks = []
    for st in subtopics:
        tasks.append(_web_search_subagent(st))
        tasks.append(_document_analysis_subagent(st))
    results = await asyncio.gather(*tasks)
    return FindingSet(topic="solid-state batteries", findings=list(results))


# --- synthesis: correct vs broken --------------------------------------

def synthesize_preserving(fs: FindingSet) -> list[dict]:
    """Coordinator passes COMPLETE findings. Every claim keeps its metadata."""
    claims = []
    for f in fs.findings:
        claims.append(
            {
                "text": f.claim,
                "source_url": f.source_url,
                "document_name": f.document_name,
                "page_number": f.page_number,
            }
        )
    return claims


def synthesize_stripped(fs: FindingSet) -> list[dict]:
    """ANTI-PATTERN: coordinator passes only claim text to the synthesis agent.
    The agent has nothing to cite with -> orphaned claims."""
    bare_text = [f.claim for f in fs.findings]  # metadata thrown away here
    return [{"text": t, "source_url": None, "document_name": None, "page_number": None}
            for t in bare_text]


def render_report(claims: list[dict]) -> str:
    lines = ["# Synthesis Report", ""]
    for c in claims:
        if c["source_url"]:
            cite = f"[{c['source_url']}]"
        elif c["document_name"] and c["page_number"] is not None:
            cite = f"[{c['document_name']}, p.{c['page_number']}]"
        else:
            cite = "[CITATION NEEDED]"
        lines.append(f"- {c['text']} {cite}")
    return "\n".join(lines)


async def main() -> None:
    subtopics = ["cathode chemistry", "manufacturing"]

    t0 = time.perf_counter()
    await gather_sequential(subtopics)
    seq = time.perf_counter() - t0

    t0 = time.perf_counter()
    fs = await gather_parallel(subtopics)
    par = time.perf_counter() - t0
    print(f"sequential spawn: {seq:.2f}s | parallel spawn: {par:.2f}s\n")

    good = synthesize_preserving(fs)
    bad = synthesize_stripped(fs)

    print(render_report(good), "\n")
    gr = verify_attribution(good)
    print(f"preserving metadata -> {gr.attributed}/{gr.total_claims} attributed, "
          f"complete={gr.complete}\n")

    print(render_report(bad), "\n")
    br = verify_attribution(bad)
    print(f"stripped metadata   -> {br.attributed}/{br.total_claims} attributed, "
          f"orphaned={len(br.orphaned)}")
    print("diagnosis: orphaned claims trace to the coordinator dropping metadata,\n"
          "           NOT to the synthesis agent's prompt.")


if __name__ == "__main__":
    asyncio.run(main())
