"""Generate a human-readable Markdown report from a CodeQL SARIF file."""

from __future__ import annotations

import re
import json
import argparse
from typing import Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import Counter, defaultdict

SECTION_ORDER = ("src", "scripts", "linting", "tests", "other")
SECTION_LABELS = {
    "src": "Runtime (`src/`)",
    "scripts": "Scripts (`scripts/`)",
    "linting": "Linting (`linting/`)",
    "tests": "Tests (`tests/`)",
    "other": "Other",
}
SECTION_TITLES = {
    "src": "Runtime",
    "scripts": "Scripts",
    "linting": "Linting",
    "tests": "Tests",
    "other": "Other",
}
SEVERITY_RANK = {
    "Critical": 5,
    "High": 4,
    "Medium": 3,
    "Low": 2,
    "Error": 2,
    "Warning": 1,
    "Note": 0,
}


@dataclass(frozen=True)
class RuleMeta:
    rule_id: str
    title: str
    summary: str
    default_level: str
    problem_severity: str
    security_severity: float | None
    tags: tuple[str, ...]


@dataclass
class Finding:
    rule: RuleMeta
    message: str
    path: str
    line: int | None
    column: int | None
    section: str
    count: int = 1

    @property
    def category(self) -> str:
        return "Security" if "security" in self.rule.tags else "Quality"

    @property
    def severity_label(self) -> str:
        if self.rule.security_severity is not None:
            if self.rule.security_severity >= 9.0:
                return "Critical"
            if self.rule.security_severity >= 7.0:
                return "High"
            if self.rule.security_severity >= 4.0:
                return "Medium"
            return "Low"
        severity = self.rule.problem_severity or self.rule.default_level
        if severity == "error":
            return "Error"
        if severity == "warning":
            return "Warning"
        return "Note"

    @property
    def severity_detail(self) -> str:
        if self.rule.security_severity is not None:
            return f"{self.severity_label} (CVSS {self.rule.security_severity:.1f})"
        return self.severity_label

    @property
    def location(self) -> str:
        if self.line is None:
            return self.path
        if self.column is None:
            return f"{self.path}:{self.line}"
        return f"{self.path}:{self.line}:{self.column}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sarif", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def _parse_security_severity(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _coerce_rule_meta(rule_id: str, rules: dict[str, Any]) -> RuleMeta:
    rule = rules.get(rule_id, {})
    short_description = (rule.get("shortDescription", {}) or {}).get("text", "").strip()
    full_description = (rule.get("fullDescription", {}) or {}).get("text", "").strip()
    help_text = (rule.get("help", {}) or {}).get("text", "").strip()
    name = (rule.get("name") or "").strip()
    properties = rule.get("properties", {})
    return RuleMeta(
        rule_id=rule_id,
        title=_first_non_empty(short_description, name, rule_id),
        summary=_first_non_empty(full_description, help_text, short_description, name, rule_id),
        default_level=rule.get("defaultConfiguration", {}).get("level", ""),
        problem_severity=properties.get("problem.severity", ""),
        security_severity=_parse_security_severity(properties.get("security-severity")),
        tags=tuple(properties.get("tags", [])),
    )


def _resolve_section(path: str) -> str:
    for prefix in SECTION_ORDER[:-1]:
        if path == prefix or path.startswith(f"{prefix}/"):
            return prefix
    return "other"


def _display_sections(findings: list[Finding]) -> list[str]:
    sections = ["src", "scripts", "linting", "tests"]
    if any(item.section == "other" for item in findings):
        sections.append("other")
    return sections


def _strip_sarif_links(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\(\d+\)", r"\1", text)


def _normalize_message(text: str) -> str:
    unique_lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        cleaned = _strip_sarif_links(raw_line).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_lines.append(cleaned)
    return " ".join(unique_lines)


def _build_rule_lookup(driver: dict[str, Any]) -> dict[str, Any]:
    return {rule["id"]: rule for rule in driver.get("rules", []) if isinstance(rule, dict) and "id" in rule}


def _extract_location(result: dict[str, Any]) -> tuple[str, int | None, int | None]:
    locations = result.get("locations", [])
    physical = locations[0].get("physicalLocation", {}) if locations else {}
    artifact = physical.get("artifactLocation", {})
    region = physical.get("region", {})
    return artifact.get("uri", "<unknown>"), region.get("startLine"), region.get("startColumn")


def _finding_sort_key(item: Finding) -> tuple[int, int, float, str, int, str]:
    section_index = SECTION_ORDER.index(item.section) if item.section in SECTION_ORDER else len(SECTION_ORDER)
    return (
        section_index,
        -SEVERITY_RANK[item.severity_label],
        -(item.rule.security_severity or 0.0),
        item.path,
        item.line or 0,
        item.rule.rule_id,
    )


def _collect_findings(doc: dict[str, Any]) -> tuple[list[Finding], str]:
    runs = doc.get("runs", [])
    if not runs:
        return [], ""
    run = runs[0]
    driver = run.get("tool", {}).get("driver", {})
    version = driver.get("semanticVersion", "")
    rules = _build_rule_lookup(driver)

    grouped: dict[tuple[str, str, int | None, int | None, str], Finding] = {}
    for result in run.get("results", []):
        path, line, column = _extract_location(result)
        message = _normalize_message(result.get("message", {}).get("text", ""))
        rule_id = result.get("ruleId", "<unknown>")
        rule = _coerce_rule_meta(rule_id, rules)
        key = (rule_id, path, line, column, message)
        if key in grouped:
            grouped[key].count += 1
            continue
        grouped[key] = Finding(
            rule=rule,
            message=message,
            path=path,
            line=line,
            column=column,
            section=_resolve_section(path),
        )

    findings = list(grouped.values())
    findings.sort(key=_finding_sort_key)
    return findings, version


def _section_summary(findings: list[Finding]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for section in SECTION_ORDER:
        section_findings = [item for item in findings if item.section == section]
        security_count = sum(item.count for item in section_findings if item.category == "Security")
        quality_count = sum(item.count for item in section_findings if item.category == "Quality")
        highest = "CLEAN"
        if section_findings:
            highest = max(section_findings, key=lambda item: SEVERITY_RANK[item.severity_label]).severity_label
        summary[section] = {
            "total": sum(item.count for item in section_findings),
            "security": security_count,
            "quality": quality_count,
            "highest": highest,
        }
    return summary


def _priority_actions(findings: list[Finding], limit: int = 5) -> list[Finding]:
    prioritized = sorted(
        findings,
        key=lambda item: (
            SECTION_ORDER.index(item.section) if item.section in SECTION_ORDER else len(SECTION_ORDER),
            -SEVERITY_RANK[item.severity_label],
            0 if item.category == "Security" else 1,
            -(item.rule.security_severity or 0.0),
            item.path,
            item.line or 0,
        ),
    )
    selected: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for finding in prioritized:
        key = (finding.rule.rule_id, finding.path)
        if key in seen:
            continue
        seen.add(key)
        selected.append(finding)
        if len(selected) == limit:
            break
    return selected


def _relative_sarif_path(sarif_path: Path) -> str:
    try:
        return sarif_path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return sarif_path.as_posix()


def _append_header(lines: list[str], label: str, version: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines.append(f"# CodeQL Security & Quality Report - {label}")
    lines.append("")
    lines.append(f"**Date:** {now}")
    if version:
        lines.append(f"**CodeQL Version:** {version}")
    lines.append("**Query Suites:** `security-and-quality` (Python)")
    lines.append("")
    lines.append("---")
    lines.append("")


def _append_summary(
    lines: list[str],
    findings: list[Finding],
    summary: dict[str, dict[str, Any]],
    sections: list[str],
) -> None:
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Section | Findings | Security | Quality | Highest |")
    lines.append("|---------|----------|----------|---------|---------|")
    total_findings = 0
    total_security = 0
    total_quality = 0
    for section in sections:
        stats = summary[section]
        total_findings += stats["total"]
        total_security += stats["security"]
        total_quality += stats["quality"]
        lines.append(
            f"| {SECTION_LABELS[section]} | {stats['total']} | {stats['security']} | {stats['quality']} | {stats['highest']} |"
        )
    highest_overall = (
        max((item.severity_label for item in findings), key=lambda value: SEVERITY_RANK[value]) if findings else "CLEAN"
    )
    lines.append(
        f"| **Total** | **{total_findings}** | **{total_security}** | **{total_quality}** | **{highest_overall}** |"
    )
    if findings:
        noisiest_section = max(sections, key=lambda section: summary[section]["total"])
        lines.append("")
        lines.append(
            f"{total_findings} findings were reported across {len(sections)} sections. "
            f"{SECTION_TITLES[noisiest_section]} contributes the most volume."
        )
    lines.append("")


def _group_by_section(findings: list[Finding]) -> dict[str, list[Finding]]:
    grouped_by_section: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped_by_section[finding.section].append(finding)
    return grouped_by_section


def _append_section(lines: list[str], label_text: str, section_findings: list[Finding]) -> None:
    if not section_findings:
        lines.append(f"## {label_text} - CLEAN")
        lines.append("")
        lines.append("No findings in this section.")
        lines.append("")
        return

    total_count = sum(item.count for item in section_findings)
    lines.append(f"## {label_text} - {total_count} Findings")
    lines.append("")
    for index, finding in enumerate(section_findings, start=1):
        lines.append(f"### {index}. {finding.rule.title}")
        lines.append("")
        lines.append(f"- **Severity:** {finding.severity_detail}")
        lines.append(f"- **Category:** {finding.category}")
        lines.append(f"- **Rule:** `{finding.rule.rule_id}`")
        lines.append(f"- **Location:** `{finding.location}`")
        if finding.rule.summary and finding.rule.summary != finding.message:
            lines.append(f"- **Description:** {finding.rule.summary}")
        if finding.count > 1:
            lines.append(f"- **Occurrences:** {finding.count}")
        lines.append(f"- **Message:** {finding.message}")
        lines.append("")


def _impacted_sections(label_name: str, findings: list[Finding], sections: list[str]) -> str:
    return ", ".join(
        SECTION_LABELS[section]
        for section in sections
        if any(item.section == section and item.severity_label == label_name for item in findings)
    )


def _append_priority_actions(lines: list[str], findings: list[Finding]) -> None:
    lines.append("## Priority Actions")
    lines.append("")
    for index, finding in enumerate(_priority_actions(findings), start=1):
        lines.append(
            f"{index}. `{finding.location}` - {finding.rule.title} "
            f"({finding.severity_label}, {finding.category}, {SECTION_TITLES[finding.section]})"
        )
    lines.append("")


def _append_risk_assessment(lines: list[str], findings: list[Finding], sections: list[str]) -> None:
    if not findings:
        return

    total_counts = Counter(item.severity_label for item in findings for _ in range(item.count))
    lines.append("## Risk Assessment")
    lines.append("")
    lines.append("| Severity | Count | Sections |")
    lines.append("|----------|-------|----------|")
    for label_name in ("Critical", "High", "Medium", "Low", "Error", "Warning", "Note"):
        count = total_counts.get(label_name, 0)
        if count:
            lines.append(f"| {label_name} | {count} | {_impacted_sections(label_name, findings, sections)} |")
    lines.append("")
    _append_priority_actions(lines, findings)


def _append_artifacts(lines: list[str], sarif_rel: str) -> None:
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- Raw SARIF: `{sarif_rel}`")
    lines.append("")


def _write_report(output_path: Path, label: str, sarif_path: Path, findings: list[Finding], version: str) -> None:
    summary = _section_summary(findings)
    sections = _display_sections(findings)
    grouped_by_section = _group_by_section(findings)
    lines: list[str] = []

    _append_header(lines, label, version)
    _append_summary(lines, findings, summary, sections)
    for section in sections:
        _append_section(lines, SECTION_LABELS[section], grouped_by_section.get(section, []))
    _append_risk_assessment(lines, findings, sections)
    _append_artifacts(lines, _relative_sarif_path(sarif_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    sarif_path = Path(args.sarif)
    output_path = Path(args.output)
    doc = _load_json(sarif_path)
    findings, version = _collect_findings(doc)
    _write_report(output_path, args.label, sarif_path, findings, version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
