# claude-learning

Hands-on projects built while preparing for Claude certification. Each topic
lives in its own numbered folder and is self-contained.

| Folder | Topic | What it covers |
|--------|-------|----------------|
| [`01-multi-tool-agent-loop`](01-multi-tool-agent-loop) | Multi-Tool Agent Loop | Agentic loop lifecycle on the Messages API; `stop_reason` as the authoritative loop-control signal; `tool_use` / `end_turn` handling; appending tool results to history; safety iteration caps done right. |
| [`02-hub-and-spoke-research-coordinator`](02-hub-and-spoke-research-coordinator) | Hub-and-Spoke Research Coordinator | Centralised coordination through a hub; subagent isolation and explicit context passing; broad vs narrow task decomposition; iterative refinement loops for coverage gaps; tracing failures back to coordinator decomposition. |
