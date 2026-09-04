"""Three tools for the support agent, plus a mock backend.

get_customer   -> looks up a customer by name/email, returns id + verified flag
lookup_order   -> looks up an order by id
process_refund -> refunds an amount against a customer id (GATED — see gate.py)
"""

from __future__ import annotations

GET_CUSTOMER_TOOL = {
    "name": "get_customer",
    "description": "Look up a customer by name or email and return their customer_id "
    "and identity-verification status. Call this BEFORE any refund.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name_or_email": {"type": "string", "description": "Customer name or email."},
        },
        "required": ["name_or_email"],
    },
}

LOOKUP_ORDER_TOOL = {
    "name": "lookup_order",
    "description": "Look up an order by order_id and return its details.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
        },
        "required": ["order_id"],
    },
}

PROCESS_REFUND_TOOL = {
    "name": "process_refund",
    "description": "Process a refund of `amount` against `customer_id`. Requires the "
    "customer to have been verified via get_customer earlier in this session.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string"},
            "amount": {"type": "number"},
            "reason": {"type": "string"},
        },
        "required": ["customer_id", "amount"],
    },
}

TOOLS = [GET_CUSTOMER_TOOL, LOOKUP_ORDER_TOOL, PROCESS_REFUND_TOOL]

# --- mock backend -----------------------------------------------------------

_CUSTOMERS = {
    "jane doe": {"customer_id": "CUST-1001", "verified": True, "email": "jane@example.com"},
    "jane@example.com": {"customer_id": "CUST-1001", "verified": True, "email": "jane@example.com"},
    "unverified guy": {"customer_id": "CUST-2002", "verified": False, "email": "guy@example.com"},
}

_ORDERS = {
    "ORD-500": {
        "order_id": "ORD-500", "customer_id": "CUST-1001", "item": "Wireless Headphones",
        "total": 89.99, "status": "delivered",
    },
}


def run_get_customer(name_or_email: str) -> dict:
    rec = _CUSTOMERS.get(name_or_email.strip().lower())
    if not rec:
        return {"found": False}
    return {"found": True, **rec}


def run_lookup_order(order_id: str) -> dict:
    rec = _ORDERS.get(order_id.strip().upper())
    if not rec:
        return {"found": False}
    return {"found": True, **rec}


def run_process_refund(customer_id: str, amount: float, reason: str = "") -> dict:
    """The actual refund side-effect. NEVER call this directly — always go through
    gate.execute_tool(), which enforces verification first."""
    return {
        "status": "refunded",
        "customer_id": customer_id,
        "amount": amount,
        "reason": reason or "unspecified",
    }
