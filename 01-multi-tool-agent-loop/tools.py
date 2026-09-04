"""Tool definitions and executors for the multi-tool agent loop.

Each tool has:
  - a JSON Schema `input_schema` registered with the Messages API
  - a plain Python function that executes it and returns a string result
"""

from __future__ import annotations

import ast
import operator as op

# --- Tool 1: calculator -------------------------------------------------------

CALCULATOR_TOOL = {
    "name": "calculator",
    "description": (
        "Evaluate a arithmetic expression and return the numeric result. "
        "Supports + - * / ** % and parentheses. Use this for any math."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The arithmetic expression, e.g. '(1200 * 1.08) / 12'.",
            }
        },
        "required": ["expression"],
    },
}

# Safe arithmetic evaluation (no eval()).
_ALLOWED_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv,
}
_ALLOWED_UNARYOPS = {ast.UAdd: op.pos, ast.USub: op.neg}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported expression")


def run_calculator(expression: str) -> str:
    try:
        result = _eval_node(ast.parse(expression, mode="eval"))
    except Exception as exc:  # surfaced back to the model as a tool result
        return f"Error: could not evaluate {expression!r} ({exc})"
    return str(result)


# --- Tool 2: web search (stub) ----------------------------------------------

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search the web for up-to-date facts and return a short list of results. "
        "Use this when you need information you do not already know."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            }
        },
        "required": ["query"],
    },
}

# Canned corpus so the stub is deterministic for tests/demos.
_MOCK_CORPUS = {
    "eiffel tower height": [
        {"title": "Eiffel Tower - Wikipedia", "snippet": "The Eiffel Tower is 330 metres tall."},
    ],
    "speed of light": [
        {"title": "Speed of light", "snippet": "The speed of light is 299792458 metres per second."},
    ],
    "anthropic founded": [
        {"title": "Anthropic", "snippet": "Anthropic was founded in 2021."},
    ],
}


def run_web_search(query: str) -> str:
    key = query.strip().lower()
    hits = None
    for k, v in _MOCK_CORPUS.items():
        if k in key or key in k:
            hits = v
            break
    if hits is None:
        hits = [
            {
                "title": f"Mock result for {query!r}",
                "snippet": "No canned data for this query. (Web search is a stub.)",
            }
        ]
    return "\n".join(f"- {h['title']}: {h['snippet']}" for h in hits)


# --- Registry ---------------------------------------------------------------

TOOLS = [CALCULATOR_TOOL, WEB_SEARCH_TOOL]

TOOL_EXECUTORS = {
    "calculator": lambda inp: run_calculator(inp["expression"]),
    "web_search": lambda inp: run_web_search(inp["query"]),
}


def execute_tool(name: str, tool_input: dict) -> str:
    if name not in TOOL_EXECUTORS:
        return f"Error: unknown tool {name!r}"
    return TOOL_EXECUTORS[name](tool_input)
