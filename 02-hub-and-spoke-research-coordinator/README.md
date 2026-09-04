# Hub-and-Spoke Research Coordinator

A coordinator (hub) decomposes a broad topic, dispatches **isolated** subagents
(spokes), aggregates their results, scores coverage, and **re-delegates to fill
gaps** until the whole topic is covered.

## Architecture

```
                 ┌─────────────┐
      topic ───▶ │ COORDINATOR │  owns: decomposition, dispatch,
                 │   (hub)     │        aggregation, coverage eval,
                 └──┬───────┬──┘        iterative refinement
                    │       │
        ┌───────────▼─┐   ┌─▼─────────────────┐
        │ web_search  │   │ document_analysis │   spokes — no shared memory,
        │  subagent   │   │     subagent      │   never talk to each other
        └─────────────┘   └───────────────────┘
```

All communication flows through the coordinator. Subagents only ever see the
prompt string the coordinator builds for them.

## Files

| File | Role |
|------|------|
| `coordinator.py` | The hub. `research(client, topic)` → `ResearchReport`. Decomposition, delegation, `assess_coverage`, refinement loop. |
| `subagents.py` | `web_search_subagent`, `document_analysis_subagent`, and `build_subagent_prompt` — which packs the **full** context (goal + topic + subtopic + prior-agent summary + optional targeted query) into every call. |
| `clients.py` | `AnthropicClient` (real API) and `OfflineClient` (deterministic; returns thin content for `tidal`/`fusion` on round 1 so refinement has a real gap to close). |
| `test_coordinator.py` | Offline tests + `--live`. |

## Exam points

- **Broad decomposition, not narrow.** `decompose()` enforces `MIN_SUBTOPICS = 5`
  and uses a curated breadth map for known topics so "renewable energy" yields
  solar, wind, geothermal, tidal, biomass, **and** fusion — not just solar + wind.
- **Subagent isolation.** Subagents get no inherited state. `build_subagent_prompt`
  explicitly restates the research goal, the topic, the assigned subtopic, and a
  summary of what prior agents produced. Weak subagent output → check the context
  the coordinator passed, not the subagent.
- **Iterative refinement, not single-shot.** After aggregation the coordinator
  runs `assess_coverage` (well-covered / partial / missing per subtopic). Any
  gap triggers a targeted re-delegation, up to `MAX_REFINEMENT_ROUNDS = 3`, until
  `COVERAGE_THRESHOLD = 1.0`.
- **Diagnostic.** A report missing whole categories traces to step 1
  (decomposition) — the subagents were never asked about the missing category.

## Run

```bash
pip install -r requirements.txt
python test_coordinator.py           # offline, no key
python test_coordinator.py --live    # needs ANTHROPIC_API_KEY
python coordinator.py                # live demo on "renewable energy technologies"
```

## Offline run (observed)

```
round 1 coverage: 67% | well=[solar, wind, geothermal, biomass] partial=[tidal, fusion]
round 2: delegating [tidal, fusion]
round 2 coverage: 100% | well=[solar, wind, geothermal, tidal, biomass, fusion]
full coverage in 2 rounds; all six sections substantive
```
