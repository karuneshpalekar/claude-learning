# Session Management Strategies

Three ways to carry work forward, and when each is right:

| Strategy | SDK | Right when | Wrong when |
|---|---|---|---|
| **resume** | `ClaudeAgentOptions(resume=id)` | continuing where you left off, **no files changed** | files changed since — old tool results now contradict disk (**stale context**) |
| **fork_session** | `ClaudeAgentOptions(resume=id, fork_session=True)` | exploring a divergent direction without disturbing the original session | you actually want to *continue* the one thread |
| **fresh start + summary injection** | `ClaudeAgentOptions()` + summary in the prompt | files changed — inject the structured summary, re-analyse only what changed | nothing changed and a plain resume is cheaper |

## Files

| File | Role |
|------|------|
| `make_codebase.py` | Writes `codebase/src/` — 10 TS modules, one tagged issue each. `apply_fixes()` rewrites exactly `mod01/mod03/mod06`. |
| `analyzer.py` | Deterministic checks + `AnalysisSummary.to_prompt_block()` (conclusions only, no raw code). |
| `session_strategies.py` | `Session` (name + frozen tool-result snapshot), `resume_stale`, `fork`, `fresh_start_with_summary`. |
| `compare.py` | `build_comparison()` — runs all steps, counts contradictions. |
| `pipeline.py` | Live Agent SDK: `initial_analysis` (+`rename_session`), `naive_resume_after_edits`, `divergent_fork`, `fresh_start_with_summary`. |
| `test_session_mgmt.py` | Offline tests. |

## Exam points

- **The stale-context problem.** A `Session` holds the file contents it read
  as frozen tool results. After `apply_fixes()`, `resume_stale()` reasons from
  that snapshot and produces **one contradiction per changed file** — e.g. it
  still says "await the promise in mod03" when mod03 is already `await`-ed.
- **Summary injection preserves knowledge without stale results.**
  `to_prompt_block()` is conclusions only — file → line → severity → rule →
  recommendation — with no raw source or tool output (`test_summary_is_conclusions_not_raw_tool_output`).
- **Targeted re-analysis beats full re-exploration.**
  `fresh_start_with_summary` re-reads **only** the 3 changed files from disk;
  the other 7 files' findings come straight from the summary — no wasted
  re-exploration. It reports the changed files as `resolved`, not "still fix".
- **fork_session ≠ resume.** `fork()` copies the snapshot into a new branch
  with a `parent` link; mutating the fork never touches the original
  (`test_fork_is_divergent_not_continuation`). Resume mutates/extends the one
  session.
- **Quality gap.** `build_comparison`: stale resume = 3 contradictions, fresh
  start = 0.

## Run

```bash
python make_codebase.py
python compare.py             # prints the stale-vs-fresh comparison
python test_session_mgmt.py   # offline tests
pip install -r requirements.txt
python pipeline.py            # live — needs the Claude Code CLI + a key
```

## Observed (offline)

```
STALE RESUME   : 10 advice items, 3 contradictions
   ! mod01.ts: advises fixing 'loose-equality' but it is not in the current file
   ! mod03.ts: advises fixing 'floating-promise' but it is not in the current file
   ! mod06.ts: advises fixing 'unguarded-access' but it is not in the current file

FRESH + SUMMARY: 10 advice items, 0 contradictions
   re-analysed from disk : ['mod01.ts', 'mod03.ts', 'mod06.ts']
   carried from summary  : [the other 7 modules]
```
