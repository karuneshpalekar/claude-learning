# Context Passing with Structured Metadata

A hub coordinator (Claude Agent SDK) that spawns research subagents **in
parallel**, collects their **structured findings**, and passes the **complete
metadata** to a synthesis subagent so every claim in the final report is
attributable.

## Files

| File | Role |
|------|------|
| `findings.py` | `Finding` dataclass — content fields (`claim`, `analysis`) kept **separate** from attribution metadata (`source_url`, `source_title`, `document_name`, `page_number`, `confidence`, `retrieved_by`). `FindingSet` (JSON round-trip) + `verify_attribution()`. |
| `subagent_defs.py` | Three `AgentDefinition`s: `web-search` (WebSearch/WebFetch), `document-analysis` (Read/Grep/Glob), `synthesis` (no tools). |
| `coordinator.py` | `ClaudeAgentOptions` with `allowed_tools=["Agent","Task",...]` + `agents=SUBAGENTS`; system prompt enforces parallel spawn + full-metadata hand-off. |
| `simulate.py` | Offline pipeline: `synthesize_preserving` vs `synthesize_stripped`, sequential vs parallel timing. |
| `test_context_passing.py` | Offline tests (no key/SDK needed for most). |

## Exam points

- **`allowed_tools` must contain `Agent` (or `Task`).** It is the hard gate for
  spawning subagents — binary, not runtime-configurable. `coordinator.build_options()`
  puts both in `allowed_tools`; `test_coordinator_allowedtools_gate` asserts it.
- **Separate content from attribution.** `Finding` has content fields and
  metadata fields as distinct keys. `is_attributable()` = has `source_url`, or
  has `document_name` + `page_number`.
- **Pass the complete findings array to synthesis — don't strip.**
  `synthesize_preserving()` forwards every metadata field → 4/4 claims cited.
  `synthesize_stripped()` forwards only `claim` text → 4/4 orphaned. The
  synthesis prompt is identical in both; only the coordinator's hand-off differs.
- **Diagnostic:** an unattributed claim in the report traces to the coordinator
  dropping metadata in step 3/4 — **not** to the synthesis agent's prompt.
- **Spawn independent subagents in parallel** — two `Agent` tool calls in one
  coordinator turn. `simulate.py`: 1.21 s sequential → 0.30 s parallel.

### `fork_session` vs parallel `Agent` calls

| | parallel `Agent` calls | `fork_session=True` |
|---|---|---|
| Purpose | fan out to N **independent** subagents | branch **one** existing session under a new id |
| Context | each subagent starts fresh | inherits the resumed session's full history |
| Concurrency | yes — that's the point | it's a branch, not a fan-out |
| Use for | independent research tasks | "what-if" continuations of one thread without mutating the original |

## Run

```bash
python simulate.py                 # offline, no deps
python test_context_passing.py     # offline tests
pip install -r requirements.txt
python coordinator.py               # live — needs claude-agent-sdk + Claude Code CLI + key
```

## Observed (offline)

```
sequential spawn: 1.21s | parallel spawn: 0.30s
preserving metadata -> 4/4 attributed, complete=True
stripped metadata   -> 0/4 attributed, orphaned=4
```
