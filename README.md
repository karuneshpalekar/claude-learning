# claude-learning

Hands-on projects built while preparing for Claude certification. Each topic
lives in its own numbered folder and is self-contained.

| Folder | Topic | What it covers |
|--------|-------|----------------|
| [`01-multi-tool-agent-loop`](01-multi-tool-agent-loop) | Multi-Tool Agent Loop | Agentic loop lifecycle on the Messages API; `stop_reason` as the authoritative loop-control signal; `tool_use` / `end_turn` handling; appending tool results to history; safety iteration caps done right. |
| [`02-hub-and-spoke-research-coordinator`](02-hub-and-spoke-research-coordinator) | Hub-and-Spoke Research Coordinator | Centralised coordination through a hub; subagent isolation and explicit context passing; broad vs narrow task decomposition; iterative refinement loops for coverage gaps; tracing failures back to coordinator decomposition. |
| [`03-structured-metadata-context-passing`](03-structured-metadata-context-passing) | Context Passing with Structured Metadata | `allowedTools` must include `Agent`/`Task`; separating content from source attribution; why stripped metadata causes downstream attribution errors; parallel subagent spawning for latency; `fork_session` vs parallel Task calls. |
| [`04-prerequisite-gate-financial-ops`](04-prerequisite-gate-financial-ops) | Prerequisite Gate for Financial Operations | Programmatic enforcement vs prompt-based guidance for financial ops; prerequisite gates that physically block a tool call until preconditions are met; structured handoff protocols with all required fields; decomposing and parallel-handling multi-concern requests. |
