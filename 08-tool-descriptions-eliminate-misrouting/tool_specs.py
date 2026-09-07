"""Two tool specs in two versions.

v1: one vague sentence each — the misrouting scenario.
v2: production-grade — purpose, inputs w/ formats, example queries, edge cases,
    and an explicit boundary against the other tool.

`ToolSpec.render()` produces the actual description string handed to the MCP
tool. The structured fields are also what the router simulation reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolSpec:
    name: str
    purpose: str
    inputs: str = ""
    examples: list[str] = field(default_factory=list)
    edge_cases: str = ""
    boundary: str = ""            # should name the sibling tool
    input_signals: list[str] = field(default_factory=list)  # regexes hinting this tool

    def render(self) -> str:
        parts = [self.purpose]
        if self.inputs:
            parts.append(f"Inputs: {self.inputs}")
        if self.examples:
            parts.append("Example queries: " + "; ".join(f'"{e}"' for e in self.examples) + ".")
        if self.edge_cases:
            parts.append(f"Edge cases: {self.edge_cases}")
        if self.boundary:
            parts.append(self.boundary)
        return " ".join(parts)


# --- v1: intentionally ambiguous -----------------------------------------

V1 = {
    "get_customer": ToolSpec(
        name="get_customer",
        purpose="Retrieves customer information.",
    ),
    "lookup_order": ToolSpec(
        name="lookup_order",
        purpose="Retrieves order details.",
    ),
}


# --- v2: production-grade -----------------------------------------------

V2 = {
    "get_customer": ToolSpec(
        name="get_customer",
        purpose=(
            "Fetch a customer or account profile: full name, contact email and phone, "
            "loyalty tier, and account status."
        ),
        inputs=(
            "a customer name as free text, an email address (e.g. jane@example.com), "
            "or a numeric account id (e.g. 1002)."
        ),
        examples=[
            "who is the buyer on this ticket",
            "find the account for jane@example.com",
            "pull up the customer's contact email",
            "verify this person's identity",
        ],
        edge_cases=(
            "if you only have an order id (ORD-#####), you cannot call this tool "
            "directly — resolve the customer from the order first."
        ),
        boundary=(
            "Do NOT use for anything about a specific order, shipment, delivery status, "
            "refund, or purchase history — use lookup_order for those."
        ),
        input_signals=[r"[\w.+-]+@[\w-]+\.\w+", r"\baccount\s+\d+", r"\bcustomer\b", r"\bbuyer\b"],
    ),
    "lookup_order": ToolSpec(
        name="lookup_order",
        purpose=(
            "Fetch details of one specific order or purchase: line items, totals, order "
            "status, delivery and shipping status, tracking, and refund state."
        ),
        inputs=(
            "an order id in the form ORD-##### (e.g. ORD-5521), or a phrase identifying "
            "an order such as 'my latest purchase', 'the order from yesterday', or "
            "'the last transaction'."
        ),
        examples=[
            "what's the delivery status of my latest purchase",
            "show all orders placed by this shopper",
            "cancel the order from yesterday",
            "verify the shipping address on this order",
            "what did this person order most recently",
        ],
        edge_cases=(
            "to list which orders belong to a customer you may first need their account "
            "id from get_customer."
        ),
        boundary=(
            "Do NOT use for customer profile, contact details, or account status — "
            "use get_customer for those."
        ),
        input_signals=[r"\bORD-\d+", r"\border(s|ed)?\b", r"\bpurchase\b", r"\bdelivery\b",
                       r"\bshipping\b", r"\btransaction\b", r"\brefund\b"],
    ),
}


def checklist(spec: ToolSpec, sibling: str) -> dict[str, bool]:
    """The 5-element production-grade test."""
    checks = {
        "has_purpose": bool(spec.purpose),
        "mentions_input_formats": any(tok in spec.inputs.lower()
                                      for tok in ("e.g.", "@", "ord-", "id")),
        "has_examples": len(spec.examples) >= 2,
        "has_edge_cases": bool(spec.edge_cases),
        "has_boundary_vs_sibling": sibling in spec.boundary and "do not" in spec.boundary.lower(),
    }
    checks["substantive_length"] = len(spec.render()) >= 200  # well past a one-liner
    return checks
