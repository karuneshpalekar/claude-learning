"""AgentDefinition objects for the three spokes.

Each subagent gets a scoped tool set matching its role:
  - web-search       -> WebSearch / WebFetch only
  - document-analysis -> Read / Grep / Glob only
  - synthesis        -> no retrieval tools; works purely from the structured
                        findings the coordinator hands it

Requires: pip install claude-agent-sdk
"""

from __future__ import annotations

from claude_agent_sdk import AgentDefinition

_FINDING_SHAPE = """
Return a JSON array of findings. Each finding MUST be an object with:
  claim          (string)  - one factual assertion
  analysis       (string)  - interpretation / caveats ("" if none)
  retrieved_by   (string)  - "web_search" or "document_analysis"
  source_url     (string|null)      - REQUIRED for web_search findings
  source_title   (string|null)
  document_name  (string|null)      - REQUIRED for document_analysis findings
  page_number    (integer|null)     - REQUIRED for document_analysis findings
  confidence     (number 0.0-1.0)
Never emit a claim you cannot attribute.
""".strip()


WEB_SEARCH_AGENT = AgentDefinition(
    description="Searches the web and returns findings, each with a source URL and page title.",
    prompt=(
        "You are a web-search researcher. For the assigned subtopic, search the web, "
        "read the most relevant pages, and extract factual findings.\n\n"
        "Every finding you return MUST include the exact source_url it came from and "
        "the page's source_title. Set retrieved_by to \"web_search\".\n\n" + _FINDING_SHAPE
    ),
    tools=["WebSearch", "WebFetch"],
    model="sonnet",
    maxTurns=6,
)

DOCUMENT_ANALYSIS_AGENT = AgentDefinition(
    description="Analyses local reference documents and returns findings with document name and page number.",
    prompt=(
        "You are a document analyst. For the assigned subtopic, locate relevant passages "
        "in the provided reference documents and extract findings with interpretation.\n\n"
        "Every finding MUST include the document_name and the 1-indexed page_number it came "
        "from, plus your analysis. Set retrieved_by to \"document_analysis\".\n\n" + _FINDING_SHAPE
    ),
    tools=["Read", "Grep", "Glob"],
    model="sonnet",
    maxTurns=6,
)

SYNTHESIS_AGENT = AgentDefinition(
    description="Synthesises a cited report from structured findings. Has no retrieval tools.",
    prompt=(
        "You are a synthesis writer. You receive a COMPLETE JSON array of findings, each "
        "carrying its own attribution metadata (source_url or document_name+page_number).\n\n"
        "Write a report in which EVERY factual sentence ends with a citation built from that "
        "metadata: '[title](url)' for web findings, '[document, p.N]' for document findings. "
        "If a finding lacks attribution, flag it — do not silently drop the citation.\n\n"
        "Also return a JSON array `claims`: [{text, source_url, document_name, page_number}] "
        "so attribution can be verified programmatically."
    ),
    tools=[],  # synthesis works only from what the coordinator passes in
    model="sonnet",
    maxTurns=3,
)

SUBAGENTS = {
    "web-search": WEB_SEARCH_AGENT,
    "document-analysis": DOCUMENT_ANALYSIS_AGENT,
    "synthesis": SYNTHESIS_AGENT,
}
