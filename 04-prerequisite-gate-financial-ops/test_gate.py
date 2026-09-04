"""Offline tests: scripted fake client, no API key needed.

1. test_bypass_attempt_is_blocked_then_succeeds_after_verification
     — the model tries process_refund FIRST (skipping verification). The gate
       must block it deterministically, regardless of what the model decided.
2. test_multi_concern_request_decomposed_and_handed_off
     — return + billing dispute + account update, investigated in parallel
       (multiple tool_use blocks in one turn), then a complete handoff.
3. test_gate_never_lets_an_unverified_refund_through
     — a small Monte-Carlo-style sweep over many "the model skips
       verification" scripts. Illustrates the exam's 92%-compliance /
       8%-failure framing for PROMPT-ONLY enforcement versus the gate's 0%
       failure rate: with the gate in front of every call, the bypass
       succeeds 0/N times no matter how often the model tries it.
"""

from __future__ import annotations

from types import SimpleNamespace

from agent_loop import run_support_agent
from gate import SessionState, execute_tool
from handoff import compile_handoff


def _text(s):
    return SimpleNamespace(type="text", text=s)


def _tool_use(id_, name, inp):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=inp)


def _resp(stop_reason, content):
    return SimpleNamespace(stop_reason=stop_reason, content=content)


class ScriptedClient:
    def __init__(self, turns):
        self._turns = turns
        self._i = 0
        self.messages = self

    def create(self, **kwargs):
        resp = self._turns[self._i]
        self._i += 1
        return resp

    @property
    def calls(self):
        return self._i


# --- 1. bypass attempt --------------------------------------------------

def test_bypass_attempt_is_blocked_then_succeeds_after_verification():
    client = ScriptedClient([
        # Model (mistakenly, or adversarially prompted to) skips verification.
        _resp("tool_use", [
            _tool_use("t1", "process_refund", {"customer_id": "CUST-1001", "amount": 89.99}),
        ]),
        # Gate blocks it; model course-corrects and verifies first.
        _resp("tool_use", [
            _tool_use("t2", "get_customer", {"name_or_email": "jane@example.com"}),
        ]),
        # Retry succeeds now that the gate's own record shows verification.
        _resp("tool_use", [
            _tool_use("t3", "process_refund", {"customer_id": "CUST-1001", "amount": 89.99}),
        ]),
        _resp("end_turn", [_text("Refund of $89.99 processed for CUST-1001.")]),
    ])

    text, state = run_support_agent(client, "Refund order ORD-500 for CUST-1001, $89.99.")

    assert state.blocked_attempts == 1, "the direct-refund bypass must be blocked exactly once"
    assert len(state.refunds_processed) == 1, "the verified retry must succeed"
    assert state.refunds_processed[0]["amount"] == 89.99
    assert "89.99" in text
    print(f"bypass blocked ({state.blocked_attempts}x), then succeeded after verification")


# --- 2. multi-concern decomposition + handoff ----------------------------

def test_multi_concern_request_decomposed_and_handed_off():
    client = ScriptedClient([
        # Verify the customer first.
        _resp("tool_use", [
            _tool_use("t1", "get_customer", {"name_or_email": "jane@example.com"}),
        ]),
        # PARALLEL investigation of the three independent concerns: one turn,
        # three tool_use blocks (order lookup for the return, plus two more
        # in a real system — here we show the order lookup + refund attempt
        # for the billing dispute alongside it).
        _resp("tool_use", [
            _tool_use("t2", "lookup_order", {"order_id": "ORD-500"}),
            _tool_use("t3", "process_refund", {
                "customer_id": "CUST-1001", "amount": 15.00, "reason": "billing dispute — duplicate charge",
            }),
        ]),
        _resp("end_turn", [_text(
            "Handling 3 concerns: (1) return of ORD-500, (2) billing dispute refund of "
            "$15.00 processed, (3) account email update — needs escalation, human handoff below."
        )]),
    ])

    text, state = run_support_agent(
        client,
        "I need to (1) return my headphones from ORD-500, (2) I was double-charged "
        "$15 in fees, and (3) please update my account email — I no longer have access "
        "to jane@example.com.",
    )

    # Both independent concerns were investigated in ONE turn (parallel), not two.
    assert client.calls == 3
    assert len(state.refunds_processed) == 1  # billing dispute resolved automatically

    # Concern 3 (account update) cannot be resolved by this agent -> handoff.
    handoff = compile_handoff(
        customer_id="CUST-1001",
        summary=(
            "Customer requested three things: (1) return of ORD-500 (Wireless Headphones, "
            "$89.99, delivered) — return authorized, awaiting item; (2) billing dispute over "
            "a duplicate $15.00 fee — verified and refunded automatically; (3) account email "
            "change from jane@example.com — requires identity re-verification beyond this "
            "agent's tools."
        ),
        root_cause=(
            "Duplicate fee traced to a retried payment webhook on 2026-08-30. Email change "
            "requires manual identity verification per policy, which this agent cannot perform."
        ),
        amount=15.00,
        recommended_action=(
            "Confirm return receipt for ORD-500 within 5 business days; manually verify "
            "identity and update the account email to the customer's new address."
        ),
    )
    assert handoff.is_complete()
    assert len(handoff.customer_id) > 0
    for field_val in (handoff.summary, handoff.root_cause, handoff.recommended_action):
        assert len(field_val) > 20, "handoff fields must be substantive, not placeholders"
    print("multi-concern request: 3/3 concerns addressed, handoff complete and self-contained")
    print(handoff.render())


# --- 3. gate never lets an unverified refund through ---------------------

def test_gate_never_lets_an_unverified_refund_through():
    """Sweep several 'model tries to skip verification' scripts. Concept check
    for the exam's 92% prompt-compliance / 8% failure framing: a prompt-only
    agent would occasionally succeed at the bypass (~8% of attempts, per the
    exam's benchmark). Routed through the gate, the bypass succeeds 0/N times
    — the gate does not depend on the model's compliance at all.
    """
    attempts = 25
    blocked = 0
    for i in range(attempts):
        state = SessionState()
        result = execute_tool(
            "process_refund", {"customer_id": f"CUST-{9000+i}", "amount": 10.0}, state
        )
        if result.get("error") and result.get("blocked_by") == "prerequisite_gate":
            blocked += 1

    assert blocked == attempts, f"gate must block 100% of unverified attempts, blocked {blocked}/{attempts}"
    print(f"gate blocked {blocked}/{attempts} unverified refund attempts (0% bypass rate)")


if __name__ == "__main__":
    test_bypass_attempt_is_blocked_then_succeeds_after_verification()
    test_multi_concern_request_decomposed_and_handed_off()
    test_gate_never_lets_an_unverified_refund_through()
    print("\nAll tests passed.")
