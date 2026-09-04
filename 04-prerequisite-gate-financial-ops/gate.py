"""Programmatic prerequisite gate for process_refund.

Exam concept: prompt instructions ("always verify before refunding") are
followed by the model most of the time but not all of the time — the exam's
benchmark figure is a 92% compliance rate, i.e. an 8% failure rate, because
compliance is probabilistic. A gate that runs in your own code, outside the
model's control, is deterministic: it either lets the call through or it
doesn't. That is 0% failure by construction, not by prompting harder.

The gate never trusts the model's claim that a customer is verified — it only
trusts its OWN record of a prior get_customer() call that returned
verified=True for that exact customer_id, in THIS session.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tools import run_get_customer, run_lookup_order, run_process_refund


class GateBlocked(Exception):
    """Raised (and turned into a tool_result error) when a prerequisite is missing."""


@dataclass
class SessionState:
    """Session-scoped, server-side state. The model never writes to this
    directly — it is only ever updated by the coordinator after a tool
    actually executes."""

    verified_customer_ids: set[str] = field(default_factory=set)
    refunds_processed: list[dict] = field(default_factory=list)
    blocked_attempts: int = 0

    def record_customer_lookup(self, result: dict) -> None:
        if result.get("found") and result.get("verified"):
            self.verified_customer_ids.add(result["customer_id"])

    def is_verified(self, customer_id: str) -> bool:
        return customer_id in self.verified_customer_ids


def execute_tool(name: str, tool_input: dict, state: SessionState) -> dict:
    """The ONLY entry point subagents/loops should call. Enforces the gate
    before process_refund ever reaches the mock backend.
    """
    if name == "get_customer":
        result = run_get_customer(tool_input["name_or_email"])
        state.record_customer_lookup(result)
        return result

    if name == "lookup_order":
        return run_lookup_order(tool_input["order_id"])

    if name == "process_refund":
        customer_id = tool_input.get("customer_id", "")
        if not state.is_verified(customer_id):
            state.blocked_attempts += 1
            return {
                "error": True,
                "blocked_by": "prerequisite_gate",
                "reason": (
                    f"process_refund blocked: customer_id={customer_id!r} has not been "
                    "verified in this session. Call get_customer first and confirm "
                    "verified=true before retrying."
                ),
            }
        result = run_process_refund(**tool_input)
        state.refunds_processed.append(result)
        return result

    return {"error": True, "reason": f"unknown tool {name!r}"}
