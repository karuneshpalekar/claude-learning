"""Writes codebase/src/ — 10 tiny TS modules, each with one tagged issue.

Fixed content + fixed order so the stale-context demo is reproducible.
`apply_fixes()` later rewrites exactly 3 of them.
"""

from __future__ import annotations

import pathlib

MODULES: list[tuple[str, str]] = [
    ("src/mod01.ts", """
export function sameId(a: string, b: string): boolean {
  return a == b;            // loose-equality
}
"""),
    ("src/mod02.ts", """
export function wrap(value: any): { value: any } {   // any-type
  return { value };
}
"""),
    ("src/mod03.ts", """
const repo = { save: async (x: unknown) => x };
export async function persist(x: unknown): Promise<void> {
  repo.save(x);             // floating-promise (result dropped)
}
"""),
    ("src/mod04.ts", """
export function greet(name: string): string {
  console.log("greeting " + name);   // debug-logging
  return "hi " + name;
}
"""),
    ("src/mod05.ts", """
export function isZero(n: number): boolean {
  return n == 0;            // loose-equality
}
"""),
    ("src/mod06.ts", """
interface Cfg { db?: { host?: string } }
export function dbHost(cfg: Cfg): string {
  return cfg.db.host;       // unguarded-access (cfg.db may be undefined)
}
"""),
    ("src/mod07.ts", """
export function merge(a: any, b: any): any {   // any-type
  return { ...a, ...b };
}
"""),
    ("src/mod08.ts", """
export function track(event: string): void {
  console.log("event: " + event);   // debug-logging
}
"""),
    ("src/mod09.ts", """
const bus = { emit: async (e: string) => e };
export async function fire(e: string): Promise<void> {
  bus.emit(e);             // floating-promise
}
"""),
    ("src/mod10.ts", """
export function done(status: string): boolean {
  return status == "done"; // loose-equality
}
"""),
]

# The 3 files step 3 modifies.
CHANGED_FILES = ["mod01.ts", "mod03.ts", "mod06.ts"]

_FIXED_BODIES = {
    "src/mod01.ts": """
export function sameId(a: string, b: string): boolean {
  return a === b;           // fixed: strict equality
}
""",
    "src/mod03.ts": """
const repo = { save: async (x: unknown) => x };
export async function persist(x: unknown): Promise<void> {
  await repo.save(x);       // fixed: awaited
}
""",
    "src/mod06.ts": """
interface Cfg { db?: { host?: string } }
export function dbHost(cfg: Cfg): string {
  return cfg.db?.host ?? "localhost";   // fixed: guarded access + default
}
""",
}


def write(root: pathlib.Path) -> list[pathlib.Path]:
    written = []
    for rel, body in MODULES:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body.lstrip("\n"))
        written.append(p)
    return written


def apply_fixes(root: pathlib.Path) -> list[str]:
    for rel, body in _FIXED_BODIES.items():
        (root / rel).write_text(body.lstrip("\n"))
    return list(CHANGED_FILES)


if __name__ == "__main__":
    root = pathlib.Path(__file__).parent / "codebase"
    paths = write(root)
    print(f"wrote {len(paths)} modules under {root}")
