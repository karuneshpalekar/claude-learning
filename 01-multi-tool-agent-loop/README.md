# Multi-Tool Agent Loop

A minimal agentic loop on the Claude Messages API with two tools, where
**`stop_reason` is the only thing that controls the loop**.

## Files

| File | Purpose |
|------|---------|
| `tools.py` | Two tools: `calculator` (safe arithmetic, no `eval`) and `web_search` (deterministic stub). Each has a JSON Schema `input_schema` and an executor function. |
| `agent_loop.py` | `run_agent(client, prompt)` — the loop. Calls `messages.create()`, switches on `response.stop_reason`. |
| `test_agent_loop.py` | Offline scripted-client test (2 sequential tool calls → `end_turn`) plus an opt-in `--live` test. |

## The loop

```
while iteration <= MAX_ITERATIONS:      # 20 — safety bound ONLY
    response = client.messages.create(model, tools, messages, ...)
    match response.stop_reason:
        "tool_use" -> append assistant turn (verbatim response.content)
                      execute each tool_use block
                      append user turn of tool_result blocks
                      continue
        "end_turn" -> return concatenated text blocks   # normal exit
        other      -> raise (don't guess)
```

Key points the exam cares about:

- **`stop_reason` is authoritative.** We never inspect content types or parse
  natural language to decide whether to continue.
- **`tool_use` handling** appends *both* the assistant message (with the
  `tool_use` blocks) and a following user message whose content is a list of
  `{"type": "tool_result", "tool_use_id": ..., "content": ...}` blocks.
- **`end_turn` handling** extracts the text blocks from the final response and
  returns them.
- **`MAX_ITERATIONS = 20` is a fallback**, not the stopping mechanism. It only
  logs a warning if hit. Normal runs terminate via `end_turn` in 2–4
  iterations.

## Run

```bash
pip install -r requirements.txt

# Offline — scripted fake client, no API key needed
python test_agent_loop.py

# Live — real model, needs a key
export ANTHROPIC_API_KEY=sk-ant-...
python test_agent_loop.py --live
python agent_loop.py
```

## Example (offline)

```
iteration 1 -> stop_reason=tool_use   web_search({'query': 'eiffel tower height'})
iteration 2 -> stop_reason=tool_use   calculator({'expression': '330 * 3.28084'})
iteration 3 -> stop_reason=end_turn   done after 3 iteration(s)
```
