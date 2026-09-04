"""Exercise the loop through a multi-step, sequential tool-call scenario.

Runs offline by default with a scripted fake client that returns the same
response shape as the Messages API. Set ANTHROPIC_API_KEY and pass --live to
run the identical loop against the real model.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

from agent_loop import run_agent
from tools import run_calculator, run_web_search


# --- Fake Messages API client ---------------------------------------------

def _text(s):
    return SimpleNamespace(type="text", text=s)


def _tool_use(id_, name, inp):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=inp)


def _resp(stop_reason, content):
    return SimpleNamespace(stop_reason=stop_reason, content=content)


class ScriptedClient:
    """Returns a pre-planned sequence of responses, ignoring inputs.

    Scenario: search the Eiffel Tower height, then calculate metres -> feet.
    Two tool_use turns, then end_turn — proving the loop iterates correctly.
    """

    def __init__(self):
        self._turns = [
            _resp("tool_use", [
                _text("I'll look up the height first."),
                _tool_use("t1", "web_search", {"query": "eiffel tower height"}),
            ]),
            _resp("tool_use", [
                _text("330 metres. Now converting to feet."),
                _tool_use("t2", "calculator", {"expression": "330 * 3.28084"}),
            ]),
            _resp("end_turn", [
                _text("The Eiffel Tower is 330 m, which is about 1082.68 feet."),
            ]),
        ]
        self._i = 0
        self.messages = self  # so client.messages.create works

    def create(self, **kwargs):
        resp = self._turns[self._i]
        self._i += 1
        return resp

    @property
    def calls(self):
        return self._i


def test_unit_tools():
    assert run_calculator("330 * 3.28084") == str(330 * 3.28084)
    assert run_calculator("2 ** 10") == "1024"
    assert "could not evaluate" in run_calculator("__import__('os')")
    assert "330 metres" in run_web_search("Eiffel Tower height")
    print("unit tool tests passed")


def test_offline_loop():
    client = ScriptedClient()
    answer = run_agent(client, "How tall is the Eiffel Tower in feet?")
    assert client.calls == 3, f"expected 3 model calls (2 tool + 1 final), got {client.calls}"
    assert "1082" in answer, answer
    print(f"offline loop passed: {client.calls} iterations, answer -> {answer!r}")


def test_live_loop():
    from anthropic import Anthropic

    client = Anthropic()
    answer = run_agent(
        client,
        "Search for the height of the Eiffel Tower in metres, then use the "
        "calculator to convert it to feet (1 m = 3.28084 ft). Give the answer in feet.",
    )
    assert answer
    print(f"live loop passed: answer -> {answer!r}")


if __name__ == "__main__":
    test_unit_tools()
    test_offline_loop()
    if "--live" in sys.argv:
        test_live_loop()
    print("\nAll tests passed.")
