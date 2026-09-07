"""Before/after evaluation of the 10 queries under v1 vs v2 descriptions."""

from __future__ import annotations

from dataclasses import dataclass

from queries import QUERIES
from router_sim import select_tool
from tool_specs import V1, V2


@dataclass
class Row:
    query: str
    expected: str
    v1_pick: str
    v2_pick: str

    @property
    def v1_ok(self) -> bool:
        return self.v1_pick == self.expected

    @property
    def v2_ok(self) -> bool:
        return self.v2_pick == self.expected


@dataclass
class Eval:
    rows: list[Row]

    @property
    def v1_accuracy(self) -> str:
        return f"{sum(r.v1_ok for r in self.rows)}/{len(self.rows)}"

    @property
    def v2_accuracy(self) -> str:
        return f"{sum(r.v2_ok for r in self.rows)}/{len(self.rows)}"

    @property
    def v1_misroutes(self) -> list[Row]:
        return [r for r in self.rows if not r.v1_ok]

    @property
    def fixed_by_v2(self) -> list[Row]:
        return [r for r in self.rows if not r.v1_ok and r.v2_ok]

    @property
    def regressed(self) -> list[Row]:
        return [r for r in self.rows if r.v1_ok and not r.v2_ok]

    def render(self) -> str:
        L = [f"{'QUERY':<48} {'expected':<13} {'v1':<13} {'v2':<13}", "-" * 88]
        for r in self.rows:
            m1 = "" if r.v1_ok else "  <-misrouted"
            L.append(f"{r.query:<48} {r.expected:<13} {r.v1_pick:<13} {r.v2_pick:<13}{m1}")
        L += [
            "-" * 88,
            f"accuracy   v1: {self.v1_accuracy}      v2: {self.v2_accuracy}",
            f"misrouted by v1 : {[r.query for r in self.v1_misroutes]}",
            f"fixed by v2     : {[r.query for r in self.fixed_by_v2]}",
            f"regressed by v2 : {[r.query for r in self.regressed]}",
        ]
        return "\n".join(L)


def run_eval() -> Eval:
    v1_specs = list(V1.values())
    v2_specs = list(V2.values())
    rows = []
    for q, expected in QUERIES:
        p1, _ = select_tool(q, v1_specs)
        p2, _ = select_tool(q, v2_specs)
        rows.append(Row(q, expected, p1, p2))
    return Eval(rows)


if __name__ == "__main__":
    print(run_eval().render())
