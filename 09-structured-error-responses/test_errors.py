"""Offline tests — error contract, empty-vs-failure distinction, recovery branches."""

from __future__ import annotations

import json

from errors import CATEGORIES, RECOVERY_ACTION, is_structured_error, make_error, valid_empty_result
from mcp_tools import lookup
from recovery_loop import MAX_TRANSIENT_ATTEMPTS, recover


def _payload(tool_result):
    return json.loads(tool_result["content"][0]["text"])


# --- 1-3. error contract ------------------------------------------------

def test_every_error_has_exactly_three_fields():
    for cat in CATEGORIES:
        e = make_error(cat)
        assert set(e) == {"errorCategory", "isRetryable", "description"}, e
        assert e["errorCategory"] == cat
        assert isinstance(e["isRetryable"], bool)
        assert e["description"].endswith(".") and len(e["description"]) > 20
    assert make_error("transient")["isRetryable"] is True
    for cat in ("validation", "business", "permission"):
        assert make_error(cat)["isRetryable"] is False, f"{cat} must not be retryable"
    print("4 categories, each exactly {errorCategory, isRetryable, description}; only transient retryable")


def test_mcp_tool_marks_error_envelope():
    for cat in CATEGORIES:
        r = lookup("CUST-10001", cat)
        assert r.get("is_error") is True
        assert _payload(r)["errorCategory"] == cat


# --- 4. valid empty result vs access failure --------------------------

def test_empty_result_is_not_an_error():
    empty = lookup("CUST-99999", "")           # well-formed, absent -> empty
    ep = _payload(empty)
    assert empty.get("is_error") is None
    assert ep == {"isError": False, "resultCount": 0, "results": []}
    assert not is_structured_error(ep)

    fail = lookup("CUST-10001", "transient")    # access failure
    fp = _payload(fail)
    assert fail["is_error"] is True
    assert fp["errorCategory"] == "transient" and fp["isRetryable"] is True

    assert ep.keys() != fp.keys()              # structurally different
    print("empty result {isError:false,resultCount:0} is structurally distinct from a transient failure")


def test_recover_never_retries_a_successful_empty_query():
    calls = {"n": 0}

    def tool(identifier, mode):
        calls["n"] += 1
        return lookup(identifier, "empty")

    out = recover(tool, "CUST-99999", "empty")
    assert out.resolved is True
    assert out.action == "accept_empty_result"
    assert out.attempts == 1 and calls["n"] == 1, "must NOT retry a successful empty result"
    print("recovery loop accepts the empty result on the first call (no wasted retry)")


# --- 5. recovery branches --------------------------------------------

def test_transient_retries_with_exponential_backoff_then_recovers():
    seq = ["transient", "transient", "none"]

    def stepping_tool(identifier, mode):
        stepping_tool.i += 1
        return lookup(identifier, seq[stepping_tool.i])
    stepping_tool.i = -1

    delays = []
    out = recover(stepping_tool, "CUST-10001", "transient", sleep=delays.append)
    assert out.resolved is True and out.attempts == 3
    assert delays == [0.5, 1.0], delays          # exponential: 0.5, then 1.0
    print(f"transient: retried {out.attempts-1}x with backoff {delays}, then succeeded")


def test_transient_that_never_heals_escalates_after_budget():
    def tool(identifier, mode):
        return lookup(identifier, "transient")

    out = recover(tool, "CUST-10001", "transient", sleep=lambda _s: None)
    assert out.resolved is False
    assert out.action == "escalate_to_human"
    assert out.attempts == MAX_TRANSIENT_ATTEMPTS
    print(f"transient never heals -> escalate after {out.attempts} attempts")


def test_validation_reformats_input_and_resubmits():
    def tool(identifier, mode):
        # only accepts the canonical format
        return lookup(identifier, mode)

    out = recover(tool, "cust 10001", "validation")
    assert out.resolved is True
    assert out.attempts == 2
    assert out.result["resultCount"] == 1
    print("validation: reformatted 'cust 10001' -> 'CUST-10001', resubmitted, resolved")


def test_business_escalates_without_retry():
    def tool(identifier, mode):
        return lookup(identifier, "business")

    out = recover(tool, "CUST-10001", "business")
    assert out.action == "escalate_to_human"
    assert out.attempts == 1, "business errors must never be retried"
    assert RECOVERY_ACTION["business"] == "escalate_to_human"
    print("business: escalated on first response, 0 retries")


def test_permission_requests_credentials_without_retry():
    def tool(identifier, mode):
        return lookup(identifier, "permission")

    out = recover(tool, "CUST-10001", "permission")
    assert out.action == "request_credentials"
    assert out.attempts == 1
    print("permission: requested elevated credentials, 0 retries")


if __name__ == "__main__":
    for fn in [
        test_every_error_has_exactly_three_fields,
        test_mcp_tool_marks_error_envelope,
        test_empty_result_is_not_an_error,
        test_recover_never_retries_a_successful_empty_query,
        test_transient_retries_with_exponential_backoff_then_recovers,
        test_transient_that_never_heals_escalates_after_budget,
        test_validation_reformats_input_and_resubmits,
        test_business_escalates_without_retry,
        test_permission_requests_credentials_without_retry,
    ]:
        fn()
    print("\nAll tests passed.")
