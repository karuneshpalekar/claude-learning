# Multi-Pass Code Review Pipeline

A single review pass over 14 files dilutes attention — early files get deep
analysis, late files get little, and the *same* pattern is flagged in one file
and waved through in another. The fix is **structural**, not a better prompt:
one pass per file (full attention budget each) + one cross-file integration
pass.

## Files

| File | Role |
|------|------|
| `make_sample_project.py` | Writes `sample_project/src/` — 14 TS files with planted recurring patterns and 3 cross-file issues. Fixed file order so the dilution simulation is reproducible. |
| `analyzers.py` | Deterministic static checks (`Finding`), `review_single_pass` (shrinking attention budget by file position), `review_per_file` (full budget each), `cross_file_analysis`. |
| `compare.py` | `build_comparison()` → counts, drop-off metric, cross-file issues, dilution artefacts + `render()` table. |
| `pipeline.py` | Live Agent SDK version: `file-reviewer` + `cross-file-integrator` `AgentDefinition`s, `single_pass_review()` vs `multi_pass_review()`. |
| `test_pipeline.py` | Offline tests. |

## Exam points

- **Attention dilution is positional, not capacity.** `review_single_pass`
  gives files in the first 30% every finding, the middle only the
  highest-severity one, the last third one-or-none — the same model, same
  files, worse output purely from *where* a file sits in the batch.
- **Per-file passes restore consistent depth.** `review_per_file` reports
  every finding for every file; `test_per_file_pass_is_consistent_depth`
  asserts the last file with issues is reported as fully as the first.
- **Batching still misses cross-cutting issues without an integration pass.**
  `cross_file_analysis` finds three issues no per-file pass can see:
  - `api-shape-inconsistency` — `users.ts` returns a bare array, `orders.ts`
    returns `{ data: [...] }`
  - `arg-order-mismatch` — `format.ts` defines `formatMoney(cents, currency)`,
    `cart.ts` calls `formatMoney(currency, cents)`
  - `config-key-drift` — `MAX_RETRIES` vs `MAX_RETRY`
- **The forEach artefact (the exam's example).** `.forEach(async …)` is
  flagged in `array.ts` (early, full attention) and silently approved in
  `collection.ts` (late, attention spent). Multi-pass flags both.
  `test_dilution_artefact_forEach_flagged_then_approved` locks this in.
- **Fixed sequential pipeline vs dynamic decomposition.** This pipeline is
  fixed (per-item then cross-item) because the item set — "every file" — is
  known up front. Dynamic adaptive decomposition is for tasks where the
  sub-problems aren't enumerable in advance (project 02's research
  coordinator). Both beat single-pass; they differ in *how the item list is
  produced*, not in having one.

## Run

```bash
python make_sample_project.py    # writes sample_project/
python compare.py                # prints the comparison table
python test_pipeline.py          # offline tests
pip install -r requirements.txt
python pipeline.py               # live multi-pass review — needs the CLI + a key
```

## Observed (offline)

```
FILE                     single-pass   multi-pass
types.ts                      2          2
...
collection.ts                 0          2      <- forEach + loose-eq dropped by single-pass
product.ts                    0          1
TOTAL issues                 12          18

single-pass issues, first half of files : 9
single-pass issues, second half of files: 3     <- attention dilution

cross-file issues (integration pass only):
  [high] api-shape-inconsistency
  [high] arg-order-mismatch
  [medium] config-key-drift

artefacts:
  foreach-async: flagged in ['array.ts'], approved in ['collection.ts']
  loose-equality: flagged in ['users.ts','orders.ts'], approved in ['collection.ts']
  any-type: flagged in ['types.ts','cart.ts'], approved in ['product.ts']
```
