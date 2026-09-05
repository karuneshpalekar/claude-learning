# Agent SDK Hooks: Normalisation and Policy Enforcement

Three MCP tools return the same fact ("order status") in three incompatible
wire formats. A **PostToolUse** hook normalises all three to one shape before
the model ever sees them. Two **PreToolUse** hooks physically block
`process_refund` over a threshold and `transfer_funds` without a passing
`aml_check` — before either tool executes.

> This project targets the **installed** `claude-agent-sdk` (0.2.152) callback
> contract, confirmed by introspecting the package directly (`HookMatcher`,
> `PreToolUseHookInput`/`PostToolUseHookInput`, `hookSpecificOutput.permissionDecision`,
> `updatedMCPToolOutput`) — not a recalled/guessed shape.

## Files

| File | Role |
|------|------|
| `normalize.py` | Pure functions: Unix epoch / ISO 8601 / DD-MM-YYYY → ISO date; numeric / single-char / English status → English word. Unit-testable with zero SDK dependency. |
| `mcp_tools.py` | Three `check_order_*` MCP tools (each a different wire format) + `process_refund`, `transfer_funds`, `aml_check`, registered on one `create_sdk_mcp_server`. |
| `hooks.py` | `normalize_order_result` (PostToolUse), `make_block_large_refund` / `make_require_aml_check` (PreToolUse), `make_record_aml_result` (PostToolUse), all against the real callback signature `(input_data, tool_use_id, context) -> dict`. |
| `coordinator.py` | `ClaudeAgentOptions(mcp_servers=..., hooks={"PreToolUse": [...], "PostToolUse": [...]})`. |
| `test_hooks.py` | Offline tests — hooks are plain async functions, tested directly with hand-built `input_data` dicts. |

## The real hook contract (this SDK version)

```python
async def hook(input_data: dict, tool_use_id: str | None, context) -> dict:
    ...
```

- `input_data["tool_name"]`, `input_data["tool_input"]` always present;
  `input_data["tool_response"]` only on `PostToolUse`.
- Returning `{}` = no opinion (allow / don't change anything).
- **PreToolUse block:**
  `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}`
- **PostToolUse transform (MCP tools):**
  `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedMCPToolOutput": {"content": [...]}}}`
- Registered via `HookMatcher(matcher="tool_a|tool_b", hooks=[callback])`, under
  `ClaudeAgentOptions(hooks={"PreToolUse": [...], "PostToolUse": [...]})` — note
  the exact camel-case event keys, and `matcher` (not `tool_name`/`tool_pattern`).

## Exam points

- **PostToolUse = normalisation, never blocking.** It runs *after* the tool
  executed — the side effect already happened, so there is nothing left to
  block. `normalize_order_result` only ever transforms `updatedMCPToolOutput`.
- **PreToolUse = policy, the only correct place to block.** It runs *before*
  execution and can set `permissionDecision: "deny"`, so the underlying tool
  never runs. `make_block_large_refund` and `make_require_aml_check` both do
  this — proven in `test_blocked_operations_never_execute`, which counts
  actual executor calls (0 for denied calls, exactly 1 once satisfied).
- **Deterministic > prompt-based, for financial ops.** The system prompt in
  `coordinator.py` tells the model about the $500 limit and the AML
  requirement — but the hooks enforce them regardless of what the model
  decides to do, exactly like project 04's gate, expressed on this SDK.
- **Format detection avoids day/month and code-meaning errors.**
  `ddmmyyyy_to_iso_date("03/11/2025")` → `2025-11-03` (3 Nov, not March), and
  `char_status_to_english("P")` → `"pending"` (not "processed") — both
  hand-coded rather than left to the model to infer per-call.

## Run

```bash
pip install -r requirements.txt
python test_hooks.py     # offline, no key
python coordinator.py    # live — needs the Claude Code CLI + a key
```

## Observed (offline)

```
normalize.py unit conversions correct
all three tool formats normalised to identical {date, status} shape
refund > $500 blocked pre-execution; refund <= $500 allowed
transfer blocked before aml_check; allowed after a passing aml_check is on record
blocked calls never reached the executor (0 calls); satisfied calls executed exactly once
All tests passed.
```
