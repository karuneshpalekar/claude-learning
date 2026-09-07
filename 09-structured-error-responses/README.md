# Structured Error Responses for All Four Categories

An MCP tool returns **structured** errors — `{errorCategory, isRetryable,
description}` — and a recovery loop that branches on that metadata: retry
transient, reformat validation, escalate business, request credentials for
permission. Plus the critical distinction: a **valid empty result is not an
error**.

## Files

| File | Role |
|------|------|
| `errors.py` | `CATEGORIES`, `make_error(cat)` → exactly `{errorCategory, isRetryable, description}`, `valid_empty_result()` → `{isError:false, resultCount:0, results:[]}`, `RECOVERY_ACTION` map. |
| `mcp_tools.py` | `customer_lookup(identifier, failure_mode)` MCP tool. `failure_mode` triggers `transient` / `validation` / `business` / `permission` / `empty`; error modes set the MCP `is_error` envelope **and** carry the structured payload. |
| `recovery_loop.py` | `recover(tool, identifier, failure_mode)` — the branching loop. Retry budget 3, exponential backoff 0.5s → 1.0s. |
| `pipeline.py` | Live Agent SDK: the tool + a `RECOVERY_POLICY` system prompt stating the per-category action. |
| `test_errors.py` | Offline tests. |

## Exam points

- **Exactly three fields per error.** `test_every_error_has_exactly_three_fields`
  asserts `set(payload) == {"errorCategory", "isRetryable", "description"}`.
- **`isRetryable` per category:** `transient` → `true`; `validation`,
  `business`, `permission` → `false`. `isRetryable: false` means *take an
  alternative path*, never retry as-is.
- **Empty result ≠ access failure.** `lookup("CUST-99999", "")` →
  `{isError:false, resultCount:0}` (query ran, found nothing).
  `lookup(..., "transient")` → `is_error` envelope + `{errorCategory:"transient",
  isRetryable:true}`. Structurally different keys.
- **Never retry a successful empty query** (the canonical anti-pattern).
  `test_recover_never_retries_a_successful_empty_query` — `attempts == 1`,
  action `accept_empty_result`.
- **Recovery branches:**

  | category | action | retries | test result |
  |---|---|---|---|
  | transient | `retry_with_backoff` → then escalate | ≤3, backoff `[0.5, 1.0]` | recovers on attempt 3, or escalates after 3 |
  | validation | `reformat_input`, resubmit once | 0 (of the bad input) | `"cust 10001"` → `"CUST-10001"` → resolved |
  | business | `escalate_to_human` | **0** | escalated on first response |
  | permission | `request_credentials` | **0** | credentials requested on first response |

## Run

```bash
python test_errors.py       # offline
pip install -r requirements.txt
python pipeline.py          # live — needs the Claude Code CLI + a key
```

## Observed (offline)

```
4 categories, each exactly {errorCategory, isRetryable, description}; only transient retryable
empty result {isError:false,resultCount:0} is structurally distinct from a transient failure
recovery loop accepts the empty result on the first call (no wasted retry)
transient: retried 2x with backoff [0.5, 1.0], then succeeded
transient never heals -> escalate after 3 attempts
validation: reformatted 'cust 10001' -> 'CUST-10001', resubmitted, resolved
business: escalated on first response, 0 retries
permission: requested elevated credentials, 0 retries
```
