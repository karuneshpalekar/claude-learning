# Prerequisite Gate for Financial Operations

A support agent where `process_refund` is **physically blocked** until
`get_customer` has returned a verified customer in the current session — the
check runs in your own code, not in the prompt.

## Why a gate, not a prompt

> "Always verify the customer before refunding" is a prompt instruction the
> model follows most of the time — not all of the time. The exam's framing:
> ~92% compliance from prompting alone means an **8% failure rate** on a
> financial operation. A prerequisite gate is deterministic: it checks the
> coordinator's own record of what actually happened, not what the model says
> happened, so the failure rate is **0% by construction**, not by better
> prompting.

## Files

| File | Role |
|------|------|
| `tools.py` | `get_customer`, `lookup_order`, `process_refund` tool defs + mock backend. |
| `gate.py` | `SessionState` (server-side, model can't touch it) + `execute_tool()` — the single choke point every tool call must go through. Blocks `process_refund` unless `SessionState.is_verified(customer_id)`. |
| `handoff.py` | `Handoff` dataclass (customer_id, summary, root_cause, amount, recommended_action) + `validate()` that rejects empty/placeholder fields. |
| `agent_loop.py` | `stop_reason`-driven loop (same shape as project 01) routed through `gate.execute_tool()` instead of calling tools directly. |
| `test_gate.py` | Offline scripted-client tests. |

## Exam points

- **The gate is the enforcement, the prompt is just guidance.** `SYSTEM_PROMPT`
  in `agent_loop.py` tells the model to verify first — but `gate.execute_tool()`
  checks `SessionState`, built only from tool results that actually ran, not
  from anything the model claims.
- **Bypass attempt is blocked regardless of model intent.** In
  `test_bypass_attempt_is_blocked_then_succeeds_after_verification`, the
  scripted model calls `process_refund` FIRST. The gate returns a
  `blocked_by: "prerequisite_gate"` error; only after `get_customer` runs does
  the retry succeed.
- **`test_gate_never_lets_an_unverified_refund_through`** sweeps 25 direct
  bypass attempts with no prior verification: **0/25** get through. This is
  the 0%-failure-rate side of the exam's 92%/8% framing, made concrete.
- **Structured handoff, 5 required fields.** `compile_handoff()` raises if
  `customer_id`, `summary`, `root_cause`, or `recommended_action` is empty or
  a placeholder ("TBD", "N/A", ...). The human agent who receives it has no
  transcript — the handoff must be self-contained.
- **Multi-concern decomposition + parallel investigation.** The test request
  bundles a return, a billing dispute, and an account-email change. The
  scripted agent investigates the return and the billing dispute **in one
  turn** (two `tool_use` blocks together, not two sequential turns), resolves
  the billing dispute automatically, and hands off the account-update concern
  it cannot perform itself — with all three concerns named in the summary.

## Run

```bash
pip install -r requirements.txt
python test_gate.py     # offline, no key
python agent_loop.py    # (import and call run_support_agent with a real Anthropic() client)
```

## Observed (offline)

```
bypass blocked (1x), then succeeded after verification
multi-concern request: 3/3 concerns addressed, handoff complete and self-contained
gate blocked 25/25 unverified refund attempts (0% bypass rate)
All tests passed.
```
