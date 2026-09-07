# Tool Descriptions That Eliminate Misrouting

The description is the primary signal an LLM uses to pick a tool. Two
one-sentence descriptions → misrouting. Rewrite them with purpose + inputs +
examples + edge cases + a boundary against the sibling → routing fixed, no
architecture change.

## Files

| File | Role |
|------|------|
| `tool_specs.py` | `ToolSpec` (structured: purpose, inputs, examples, edge_cases, boundary) in two versions — `V1` (one vague sentence) and `V2` (production-grade). `checklist()` = the 5-element test. `render()` builds the string the MCP tool actually carries. |
| `queries.py` | 10 labelled queries, mixed intent, including order queries with no literal "order" keyword. |
| `router_sim.py` | Deterministic model of description-driven tool selection: purpose-overlap (weak) + example near-match (strong) + input-format signal (strong); ties fall to the first tool. |
| `evaluate.py` | `run_eval()` — v1 vs v2 over the 10 queries, accuracy + fixed/regressed lists. |
| `system_prompt_audit.py` | `SYSTEM_PROMPT_V1/V2` + `audit()` — flags imperative + tool-keyword phrases and proposes routing-neutral rewrites. |
| `mcp_tools.py` | `build_server("v1"|"v2")` — the two tools with the chosen descriptions. |
| `pipeline.py` | Live Agent SDK: run the 10 queries, log the actual `ToolUseBlock` the model picks, for v1 vs v2. |
| `test_misrouting.py` | Offline tests. |

## Exam points

- **Descriptions drive selection.** `router_sim` uses *only* the description to
  choose. With V1 (`"Retrieves customer information."` / `"Retrieves order
  details."`) there's almost nothing to distinguish them, so order queries
  lacking the word "order" tie and fall to `get_customer`.
- **The 5-element production-grade description.** V2 states **purpose**,
  **inputs with formats** (`ORD-#####`, `jane@example.com`, `account 1002`),
  **example queries**, **edge cases**, and an **explicit boundary**
  (`"Do NOT use for … — use lookup_order for those."`).
  `test_v2_descriptions_are_production_grade` checks all five; V1 fails it.
- **Measured before/after, no architectural change.** Same tools, same router,
  same queries — only the description text changes:

  | | accuracy | misrouted |
  |---|---|---|
  | v1 | **7/10** | delivery status of my latest purchase; Look up ORD-5521; show all orders placed by this shopper |
  | v2 | **10/10** | — |

- **System-prompt conflicts override good descriptions.** `SYSTEM_PROMPT_V1`
  has `"Always check the customer's account details first"` and `"For every
  request, first look up the order history"` — standing pulls toward each
  tool. `audit()` flags both (imperative + tool keyword) and rewrites to
  `"Call a tool only when the user's request needs that specific data; choose
  it from the tool descriptions, not from a standing rule."` `SYSTEM_PROMPT_V2`
  audits clean.

## Run

```bash
python evaluate.py                # before/after routing table
python system_prompt_audit.py     # keyword-conflict findings
python test_misrouting.py         # offline tests
pip install -r requirements.txt
python pipeline.py                # live — real model tool selection, v1 vs v2
```

## Observed (offline)

```
accuracy   v1: 7/10      v2: 10/10
misrouted by v1 : ["What's the delivery status of my latest purchase?", 'Look up ORD-5521',
                   'Show all orders placed by this shopper']
fixed by v2     : (all three)   regressed by v2 : []

audit: 2 keyword conflicts in v1 prompt, 0 in v2 prompt
```
