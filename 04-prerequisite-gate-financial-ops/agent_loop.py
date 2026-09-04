"""Support-agent loop: same stop_reason-driven pattern as project 01, but every
tool call is routed through gate.execute_tool() instead of calling the tool
directly — that is what makes the prerequisite deterministic instead of
prompt-dependent.
"""

from __future__ import annotations

import logging
import os

from gate import SessionState, execute_tool
from tools import TOOLS

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("agent_loop")

MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-5")
MAX_ITERATIONS = 20
MAX_TOKENS = 1024

SYSTEM_PROMPT = """
You are a customer support agent for an e-commerce company. You have three
tools: get_customer, lookup_order, process_refund.

Rules (prompt-level guidance — the real enforcement is a server-side gate you
cannot see or override):
- Always call get_customer before process_refund.
- If a request has multiple distinct concerns (e.g. a return, a billing
  dispute, an account update), identify ALL of them up front and investigate
  independent ones IN PARALLEL (multiple tool calls in one turn), not one at
  a time.
- If you cannot fully resolve every concern yourself, escalate with a
  complete, self-contained handoff: customer_id, summary, root_cause, amount,
  and recommended_action. The human agent who receives it has NO access to
  this conversation — the handoff is everything they will see.
""".strip()


def _text_from(message) -> str:
    return "".join(
        b.text for b in message.content if getattr(b, "type", None) == "text"
    ).strip()


def run_support_agent(client, user_prompt: str, state: SessionState | None = None):
    """Returns (final_text, SessionState) so callers can inspect gate stats
    (blocked_attempts, refunds_processed, verified_customer_ids)."""
    state = state or SessionState()
    messages: list[dict] = [{"role": "user", "content": user_prompt}]

    for iteration in range(1, MAX_ITERATIONS + 1):
        response = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, system=SYSTEM_PROMPT,
            tools=TOOLS, messages=messages,
        )
        log.info("iteration %d -> stop_reason=%s", iteration, response.stop_reason)

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                log.info("  tool_use: %s(%s)", block.name, block.input)
                # THE GATE: every tool call — including process_refund — goes
                # through execute_tool(), never the raw tools.run_* functions.
                output = execute_tool(block.name, block.input, state)
                if output.get("error"):
                    log.warning("  BLOCKED/ERROR: %s", output.get("reason"))
                else:
                    log.info("  -> %s", output)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                        "is_error": bool(output.get("error")),
                    }
                )
            messages.append({"role": "user", "content": tool_results})
            continue

        if response.stop_reason == "end_turn":
            return _text_from(response), state

        raise RuntimeError(f"Unhandled stop_reason={response.stop_reason!r}")

    log.warning("MAX_ITERATIONS reached without end_turn")
    return _text_from(response), state
