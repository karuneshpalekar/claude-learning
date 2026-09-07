"""Offline tests — router simulation + description checklist + prompt audit."""

from __future__ import annotations

from evaluate import run_eval
from system_prompt_audit import SYSTEM_PROMPT_V1, SYSTEM_PROMPT_V2, audit
from tool_specs import V1, V2, checklist


def test_v1_descriptions_misroute():
    e = run_eval()
    v1_correct = sum(r.v1_ok for r in e.rows)
    assert v1_correct <= 7, f"v1 should misroute; got {e.v1_accuracy}"
    assert len(e.v1_misroutes) >= 2, "need at least 2-3 misroutes to demonstrate the problem"
    # the misroutes are order queries that got sent to get_customer
    for r in e.v1_misroutes:
        assert r.expected == "lookup_order" and r.v1_pick == "get_customer"
    print(f"v1: {e.v1_accuracy}, misrouted {[r.query for r in e.v1_misroutes]}")


def test_v2_descriptions_fix_routing_without_architecture_change():
    e = run_eval()
    v2_correct = sum(r.v2_ok for r in e.rows)
    assert v2_correct >= 9, f"v2 should reach >=9/10; got {e.v2_accuracy}"
    assert not e.regressed, f"v2 regressed on {[r.query for r in e.regressed]}"
    assert {r.query for r in e.fixed_by_v2} == {r.query for r in e.v1_misroutes}
    print(f"v2: {e.v2_accuracy}, fixed every v1 misroute, 0 regressions")


def test_v2_descriptions_are_production_grade():
    for name, sibling in (("get_customer", "lookup_order"), ("lookup_order", "get_customer")):
        c = checklist(V2[name], sibling)
        assert all(c.values()), f"{name} fails production-grade checklist: {c}"
        # and v1 fails it (that's the contrast)
        assert not all(checklist(V1[name], sibling).values())
    print("v2 descriptions have purpose + input formats + examples + edge cases + boundary; v1 do not")


def test_system_prompt_audit_finds_keyword_conflicts():
    conflicts = audit(SYSTEM_PROMPT_V1)
    assert len(conflicts) >= 2
    pulls = {c.pulls_toward for c in conflicts}
    assert pulls == {"get_customer", "lookup_order"}, pulls
    for c in conflicts:
        assert c.rewrite and c.imperative not in c.rewrite.lower()
    # the fixed prompt has no conflicts
    assert audit(SYSTEM_PROMPT_V2) == []
    print(f"audit: {len(conflicts)} keyword conflicts in v1 prompt, 0 in v2 prompt")


if __name__ == "__main__":
    test_v1_descriptions_misroute()
    test_v2_descriptions_fix_routing_without_architecture_change()
    test_v2_descriptions_are_production_grade()
    test_system_prompt_audit_finds_keyword_conflicts()
    print("\nAll tests passed.")
