"""A multi-tool agentic loop driven by the Messages API `stop_reason`.

Loop lifecycle
--------------
1. Send the running conversation to `client.messages.create()`.
2. Inspect `response.stop_reason` — this is the *authoritative* signal:
     - "tool_use"  -> Claude wants to call one or more tools. Execute each,
                      append the assistant turn + a user turn of tool_result
                      blocks, and loop again.
     - "end_turn"  -> Claude is done. Extract the final text and return.
     - anything else ("max_tokens", "stop_sequence", "pause_turn", ...) ->
                      stop and report it; we do not guess.
3. A MAX_ITERATIONS cap exists only as a safety bound. It is NOT the stopping
   mechanism — a healthy run always terminates via `end_turn` first.

Do not branch on content types or parse natural language to decide whether to
keep looping. `stop_reason` is deterministic; text isn't.
"""

from __future__ import annotations

import logging
import os

from tools import TOOLS, execute_tool

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("agent_loop")

MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-5")
MAX_ITERATIONS = 20  # safety bound only — never the primary stop condition
MAX_TOKENS = 1024


def _text_from(message) -> str:
    """Concatenate the text blocks of an assistant message."""
    return "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    ).strip()


def run_agent(client, user_prompt: str, *, system: str | None = None) -> str:
    """Run the agentic loop to completion and return Claude's final text.

    `client` is anything exposing `.messages.create(...)` with the Messages API
    shape (the real Anthropic SDK client, or a fake for offline tests).
    """
    messages: list[dict] = [{"role": "user", "content": user_prompt}]

    for iteration in range(1, MAX_ITERATIONS + 1):
        kwargs = dict(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=TOOLS,
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)

        log.info("iteration %d -> stop_reason=%s", iteration, response.stop_reason)

        if response.stop_reason == "tool_use":
            # 1. Record the assistant turn verbatim (text + tool_use blocks).
            messages.append({"role": "assistant", "content": response.content})

            # 2. Execute every tool_use block and collect tool_result blocks.
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                log.info("  tool_use: %s(%s)", block.name, block.input)
                output = execute_tool(block.name, block.input)
                log.info("  -> %s", output)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )

            # 3. Feed the results back as the next user turn, then loop.
            messages.append({"role": "user", "content": tool_results})
            continue

        if response.stop_reason == "end_turn":
            final_text = _text_from(response)
            messages.append({"role": "assistant", "content": response.content})
            log.info("done after %d iteration(s)", iteration)
            return final_text

        # Any other stop_reason: don't guess, surface it.
        raise RuntimeError(
            f"Unhandled stop_reason={response.stop_reason!r} on iteration {iteration}"
        )

    log.warning(
        "MAX_ITERATIONS (%d) reached without end_turn — returning best-effort text. "
        "This should never happen in normal operation; investigate the prompt/tools.",
        MAX_ITERATIONS,
    )
    return _text_from(response)


def main() -> None:
    from anthropic import Anthropic

    client = Anthropic()  # reads ANTHROPIC_API_KEY
    prompt = (
        "Search for the height of the Eiffel Tower in metres, then use the "
        "calculator to convert that height to feet (1 m = 3.28084 ft). "
        "Give me the final answer in feet."
    )
    print("\n=== FINAL ANSWER ===")
    print(run_agent(client, prompt))


if __name__ == "__main__":
    main()
