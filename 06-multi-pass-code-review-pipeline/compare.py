"""Builds the single-pass vs multi-pass comparison and the dilution-artefact list."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from analyzers import (
    Finding,
    analyze_project,
    cross_file_analysis,
    review_per_file,
    review_single_pass,
)


@dataclass
class Artefact:
    rule: str
    flagged_in: list[str]
    missed_in: list[str]


@dataclass
class Comparison:
    per_file_counts: list[tuple[str, int, int]]        # (file, single, multi)
    single_total: int
    multi_total: int
    cross_file: list[Finding]
    artefacts: list[Artefact]
    first_half_single: int
    second_half_single: int

    def render(self) -> str:
        lines = ["FILE                     single-pass   multi-pass",
                 "-" * 52]
        for name, s, m in self.per_file_counts:
            lines.append(f"{name:<24} {s:^11} {m:^10}")
        lines += [
            "-" * 52,
            f"{'TOTAL issues':<24} {self.single_total:^11} {self.multi_total:^10}",
            "",
            f"single-pass issues in first half of files : {self.first_half_single}",
            f"single-pass issues in second half of files: {self.second_half_single}   "
            f"<- drop-off = attention dilution",
            "",
            "cross-file issues (multi-pass integration pass only):",
        ]
        for f in self.cross_file:
            if f.rule.startswith("recurring:"):
                continue
            lines.append(f"  [{f.severity}] {f.rule}: {f.message}")
        lines += ["", "attention-dilution artefacts (same pattern judged differently):"]
        for a in self.artefacts:
            lines.append(f"  {a.rule}: flagged in {a.flagged_in}, silently approved in {a.missed_in}")
        return "\n".join(lines)


def build_comparison(root: Path) -> Comparison:
    analyzed = analyze_project(root)
    single = review_single_pass(analyzed)
    per_file = review_per_file(analyzed)
    cross = cross_file_analysis(analyzed)

    names = [name for name, _t, _f in analyzed]
    per_file_counts = [(n, len(single[n]), len(per_file[n])) for n in names]
    single_total = sum(len(v) for v in single.values())
    multi_total = sum(len(v) for v in per_file.values()) + len(
        [f for f in cross if not f.rule.startswith("recurring:")]
    )

    half = len(names) // 2
    first_half_single = sum(len(single[n]) for n in names[:half])
    second_half_single = sum(len(single[n]) for n in names[half:])

    # Artefacts: a rule that recurs across files but single-pass reported in
    # some and not others.
    rule_files: dict[str, list[str]] = {}
    for name, _t, findings in analyzed:
        for f in findings:
            rule_files.setdefault(f.rule, [])
            if name not in rule_files[f.rule]:
                rule_files[f.rule].append(name)

    artefacts: list[Artefact] = []
    for rule, files in rule_files.items():
        if len(files) < 2:
            continue
        flagged = [n for n in files if any(x.rule == rule for x in single[n])]
        missed = [n for n in files if n not in flagged]
        if flagged and missed:
            artefacts.append(Artefact(rule, flagged, missed))

    return Comparison(
        per_file_counts, single_total, multi_total, cross, artefacts,
        first_half_single, second_half_single,
    )


if __name__ == "__main__":
    root = Path(__file__).parent / "sample_project"
    print(build_comparison(root).render())
