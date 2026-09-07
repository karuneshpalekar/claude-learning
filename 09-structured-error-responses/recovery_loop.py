"""Agent recovery loop: parse the error metadata, branch on errorCategory.

  transient   -> retry, up to 3 attempts, exponential backoff
  validation  -> reformat the identifier, resubmit once
  business    -> escalate to a human (NEVER retry)
  permission  -> request elevated credentials (NEVER retry)

A successful response — INCLUDING a valid empty result (resultCount: 0) — is
returned immediately. Retrying a successful empty query is the canonical
anti-pattern and this loop never does it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from errors import is_structured_error

MAX_TRANSIENT_ATTEMPTS = 3
BASE_BACKOFF_S = 0.5

# tool: (identifier, failure_mode) -> MCP-style dict {"content":[{"text": json}], "is_error"?: bool}
Tool = Callable[[str, str], dict]


@dataclass
class Outcome:
    resolved: bool
    action: str
    attempts: int
    backoffs: list[float] = field(default_factory=list)
    detail: str = ""
    result: dict | None = None


def _payload(tool_result: dict) -> dict:
    return json.loads(tool_result["content"][0]["text"])


def _reformat(identifier: str) -> str:
    digits = re.sub(r"\D", "", identifier)
    return f"CUST-{digits.zfill(5)[:5]}" if digits else identifier.strip().upper()


def recover(tool: Tool, identifier: str, failure_mode: str = "", *, sleep=None) -> Outcome:
    """`sleep` is injectable so tests don't actually wait; it receives the
    backoff duration."""
    sleep = sleep or (lambda _s: None)
    attempts = 0
    backoffs: list[float] = []
    current_id = identifier
    mode = failure_mode

    while True:
        attempts += 1
        result = tool(current_id, mode)
        payload = _payload(result)

        # --- success (including a valid empty result) ---------------------
        if not result.get("is_error") and not is_structured_error(payload):
            count = payload.get("resultCount")
            return Outcome(
                resolved=True,
                action="none" if count else "accept_empty_result",
                attempts=attempts,
                backoffs=backoffs,
                detail=f"query succeeded, resultCount={count}",
                result=payload,
            )

        # --- structured error: branch on category -----------------------
        category = payload["errorCategory"]
        retryable = payload["isRetryable"]

        if category == "transient" and retryable:
            if attempts < MAX_TRANSIENT_ATTEMPTS:
                delay = BASE_BACKOFF_S * (2 ** (attempts - 1))
                backoffs.append(delay)
                sleep(delay)
                continue
            return Outcome(False, "escalate_to_human", attempts, backoffs,
                           "transient error persisted past the retry budget", payload)

        if category == "validation":
            reformatted = _reformat(current_id)
            if reformatted != current_id:
                current_id = reformatted
                if mode == "validation":
                    mode = "none"   # drop the forced mode; resubmit the fixed id
                continue
            return Outcome(False, "escalate_to_human", attempts, backoffs,
                           "input still invalid after reformat", payload)

        if category == "business":
            return Outcome(False, "escalate_to_human", attempts, backoffs,
                           "policy violation — human override required", payload)

        if category == "permission":
            return Outcome(False, "request_credentials", attempts, backoffs,
                           "need elevated credentials, then retry", payload)

        return Outcome(False, "escalate_to_human", attempts, backoffs,
                       f"unhandled category {category!r}", payload)
