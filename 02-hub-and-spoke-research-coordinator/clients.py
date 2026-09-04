"""LLM client abstraction.

Both clients expose a single method:

    complete(system: str, prompt: str) -> str

- `AnthropicClient` calls the real Messages API.
- `OfflineClient` is a deterministic stand-in so the whole coordinator can be
  run and tested with no API key. It also *deliberately* returns thin content
  for `tidal` and `fusion` on the first attempt, so the iterative-refinement
  loop has a real gap to detect and fill on round 2.
"""

from __future__ import annotations

import os
import re


class AnthropicClient:
    def __init__(self, model: str | None = None):
        from anthropic import Anthropic

        self._client = Anthropic()
        self.model = model or os.environ.get("AGENT_MODEL", "claude-sonnet-5")

    def complete(self, system: str, prompt: str) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()


# --- Offline deterministic client ------------------------------------------

_FACTS = {
    "solar": "Photovoltaic and concentrated solar power; module costs fell ~90% since 2010; "
    "now the cheapest new generation in most markets; intermittency handled with storage.",
    "wind": "Onshore and offshore turbines; offshore capacity factors 40-55%; "
    "larger rotors and floating foundations expand viable sites.",
    "geothermal": "Hydrothermal plants plus enhanced geothermal systems (EGS) that fracture hot "
    "dry rock; provides firm baseload; drilling cost is the main barrier.",
    "tidal": "Tidal stream turbines and tidal barrages; highly predictable; limited to high-flow "
    "coastal sites; MeyGen and Sihwa Lake are the largest operating projects.",
    "biomass": "Combustion, gasification, anaerobic digestion and biogas; can be dispatchable and "
    "carbon-negative with CCS (BECCS); feedstock sustainability is contested.",
    "fusion": "Magnetic confinement (tokamaks, stellarators) and inertial confinement; NIF hit "
    "net energy gain in 2022; private firms target grid pilots in the 2030s.",
}


class OfflineClient:
    def __init__(self):
        self._attempts: dict[str, int] = {}

    def complete(self, system: str, prompt: str) -> str:
        low = prompt.lower()

        # Decomposition request -> return a broad subtopic list.
        if "decompose" in system.lower() or "subtopics" in low:
            if "renewable energy" in low:
                return "solar, wind, geothermal, tidal, biomass, fusion"
            # generic fallback: 5 neutral facets
            return "history, key technologies, current state of the art, economics, open challenges"

        # Coverage assessment request -> handled by the coordinator itself,
        # never routed here.

        # Otherwise this is a subagent research request about one subtopic.
        subtopic = _detect_subtopic(low)
        if subtopic is None:
            return "No substantive findings."

        self._attempts[subtopic] = self._attempts.get(subtopic, 0) + 1
        # Both subagents fire per round, so attempts 1-2 == round 1.
        thin_on_first = subtopic in {"tidal", "fusion"}
        if thin_on_first and self._attempts[subtopic] <= 2:
            return f"Brief mention of {subtopic}; details not found."

        kind = "Web search" if "web search" in system.lower() else "Document analysis"
        return f"{kind} findings on {subtopic}: {_FACTS[subtopic]}"


def _detect_subtopic(text: str) -> str | None:
    # Only look at the explicit assignment line, not the surrounding context
    # (which mentions other subtopics).
    m = re.search(r"your assigned subtopic:\s*([a-z ]+)", text)
    scope = m.group(1) if m else text
    for name in _FACTS:
        if re.search(rf"\b{name}\b", scope):
            return name
    return None
