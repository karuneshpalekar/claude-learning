"""10 test queries spanning customer-intent and order-intent, including
phrasings that don't contain the obvious keyword (where v1 misroutes)."""

QUERIES: list[tuple[str, str]] = [
    ("What's the delivery status of my latest purchase?", "lookup_order"),
    ("Look up ORD-5521", "lookup_order"),
    ("Show all orders placed by this shopper", "lookup_order"),
    ("Get customer information for account 1002", "get_customer"),
    ("Retrieve order details for the last transaction", "lookup_order"),
    ("Who is the customer on this ticket?", "get_customer"),
    ("Cancel the order from yesterday", "lookup_order"),
    ("Pull up the buyer's contact email", "get_customer"),
    ("What did this person order most recently?", "lookup_order"),
    ("Verify the shipping address on this order", "lookup_order"),
]
