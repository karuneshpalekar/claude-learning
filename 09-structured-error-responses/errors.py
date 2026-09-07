"""The four error categories + the valid-empty-result shape, and the
category -> recovery-action mapping.

Error payload contract: EXACTLY three fields.
    { "errorCategory": "transient"|"validation"|"business"|"permission",
      "isRetryable": bool,
      "description": "<what went wrong + what to do next>" }

Valid empty result (NOT an error):
    { "isError": false, "resultCount": 0, "results": [] }
"""

from __future__ import annotations

CATEGORIES = ("transient", "validation", "business", "permission")

# (isRetryable, description)
_SPEC: dict[str, tuple[bool, str]] = {
    "transient": (
        True,
        "The customer database timed out. This is temporary — retry the same "
        "request after a short backoff.",
    ),
    "validation": (
        False,
        "The customer identifier is malformed. Retrying as-is will fail again — "
        "reformat it to CUST-##### and resubmit.",
    ),
    "business": (
        False,
        "The requested refund exceeds the policy limit. This can never succeed "
        "automatically — escalate to a human agent for an override decision.",
    ),
    "permission": (
        False,
        "The current credentials are not authorised to read this customer record. "
        "Do not retry — request elevated credentials, then try again.",
    ),
}

# category -> what the recovery loop must DO
RECOVERY_ACTION = {
    "transient": "retry_with_backoff",
    "validation": "reformat_input",
    "business": "escalate_to_human",
    "permission": "request_credentials",
}


def make_error(category: str) -> dict:
    if category not in _SPEC:
        raise ValueError(f"unknown error category: {category!r}")
    is_retryable, description = _SPEC[category]
    return {
        "errorCategory": category,
        "isRetryable": is_retryable,
        "description": description,
    }


def valid_empty_result() -> dict:
    return {"isError": False, "resultCount": 0, "results": []}


def is_structured_error(payload: dict) -> bool:
    return set(payload) == {"errorCategory", "isRetryable", "description"}
