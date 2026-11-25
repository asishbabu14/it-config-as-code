#!/usr/bin/env python3
"""Compare desired identity state to a mock or real export.

Desired state is YAML. The live side is a JSON document shaped like a small
directory export. Both are normalized, then compared. This tool never calls
a network API. A real tenant export can be dropped in once it matches the
live schema documented in docs/architecture.md.

Exit codes:
  0  no drift
  1  drift
  2  usage or parse error
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
SIGN_ON_MODES = {
    "SAML_2_0": "saml",
    "OPENID_CONNECT": "oidc",
}


@dataclass(frozen=True)
class Group:
    description: str


@dataclass(frozen=True)
class Rule:
    group: str
    expression: str
    status: str


@dataclass(frozen=True)
class App:
    sign_on: str
    status: str
    audience: str
    assignments: frozenset[str]


@dataclass(frozen=True)
class Policy:
    state: str
    grant: frozenset[str]
    include_groups: frozenset[str]


@dataclass(frozen=True)
class State:
    groups: dict[str, Group]
    rules: dict[str, Rule]
    apps: dict[str, App]
    policies: dict[str, Policy]


@dataclass(frozen=True)
class Finding:
    severity: str
    kind: str
    path: str
    desired: str
    live: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


class DriftError(Exception):
    """Desired state or the live export could not be read."""


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DriftError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise DriftError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise DriftError(f"{path} must contain a mapping")
    return document


def load_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DriftError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DriftError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise DriftError(f"{path} must contain a JSON object")
    return document


def _require_version(document: dict[str, Any], path: Path) -> None:
    if document.get("version") != 1:
        raise DriftError(f"{path}: version must be 1")


def _index(items: list[Any], label: str, name_of) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict):
            raise DriftError(f"{label} entries must be objects")
        name = name_of(item)
        if not isinstance(name, str) or not name:
            raise DriftError(f"{label} entry is missing a name")
        if name in found:
            raise DriftError(f"duplicate {label} name: {name}")
        found[name] = item
    return found


def _string(item: dict[str, Any], key: str, label: str) -> str:
    value = item.get(key)
    if not isinstance(value, str):
        raise DriftError(f"{label} field {key} must be a string")
    return value.strip()


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DriftError(f"{label} must be a list of strings")
    return [item.strip() for item in value]


def normalize_desired(document: dict[str, Any], path: Path) -> State:
    _require_version(document, path)
    groups = _index(document.get("groups") or [], "group", lambda item: item.get("name"))
    rules = _index(document.get("rules") or [], "rule", lambda item: item.get("name"))
    apps = _index(document.get("apps") or [], "app", lambda item: item.get("name"))
    policies = _index(document.get("policies") or [], "policy", lambda item: item.get("name"))

    return State(
        groups={
            name: Group(description=_string(item, "description", f"group {name}"))
            for name, item in groups.items()
        },
        rules={
            name: Rule(
                group=_string(item, "group", f"rule {name}"),
                expression=_string(item, "expression", f"rule {name}"),
                status=_string(item, "status", f"rule {name}"),
            )
            for name, item in rules.items()
        },
        apps={
            name: App(
                sign_on=_string(item, "sign_on", f"app {name}"),
                status=_string(item, "status", f"app {name}"),
                audience=_string(item, "audience", f"app {name}"),
                assignments=frozenset(_string_list(item.get("assignments") or [], f"app {name}")),
            )
            for name, item in apps.items()
        },
        policies={
            name: Policy(
                state=_string(item, "state", f"policy {name}"),
                grant=frozenset(_string_list(item.get("grant") or [], f"policy {name} grant")),
                include_groups=frozenset(
                    _string_list(item.get("include_groups") or [], f"policy {name} groups")
                ),
            )
            for name, item in policies.items()
        },
    )


def _live_sign_on(mode: str) -> str:
    return SIGN_ON_MODES.get(mode, mode.strip().lower())


def normalize_live(document: dict[str, Any], path: Path) -> State:
    _require_version(document, path)
    try:
        raw_groups = document["groups"]
        raw_rules = document["groupRules"]
        raw_apps = document["applications"]
        raw_policies = document["conditionalAccessPolicies"]
    except KeyError as exc:
        raise DriftError(f"{path} is missing {exc.args[0]}") from exc

    groups = _index(raw_groups, "group", lambda item: (item.get("profile") or {}).get("name"))
    rules = _index(raw_rules, "rule", lambda item: item.get("name"))
    apps = _index(raw_apps, "app", lambda item: item.get("label"))
    policies = _index(raw_policies, "policy", lambda item: item.get("displayName"))

    normalized_groups: dict[str, Group] = {}
    for name, item in groups.items():
        profile = item.get("profile") or {}
        description = profile.get("description", "")
        if not isinstance(description, str):
            raise DriftError(f"group {name} description must be a string")
        normalized_groups[name] = Group(description=description.strip())

    normalized_rules: dict[str, Rule] = {}
    for name, item in rules.items():
        assignments = _string_list(item.get("groupAssignments") or [], f"rule {name}")
        group = ",".join(sorted(assignments))
        expression = ((item.get("conditions") or {}).get("expression") or {}).get("value", "")
        if not isinstance(expression, str):
            raise DriftError(f"rule {name} expression must be a string")
        normalized_rules[name] = Rule(
            group=group,
            expression=expression.strip(),
            status=_string(item, "status", f"rule {name}"),
        )

    normalized_apps: dict[str, App] = {}
    for name, item in apps.items():
        settings = (item.get("settings") or {}).get("signOn") or {}
        audience = settings.get("audience", "")
        if not isinstance(audience, str):
            raise DriftError(f"app {name} audience must be a string")
        normalized_apps[name] = App(
            sign_on=_live_sign_on(_string(item, "signOnMode", f"app {name}")),
            status=_string(item, "status", f"app {name}"),
            audience=audience.strip(),
            assignments=frozenset(_string_list(item.get("assignedGroups") or [], f"app {name}")),
        )

    normalized_policies: dict[str, Policy] = {}
    for name, item in policies.items():
        controls = (item.get("grantControls") or {}).get("builtInControls") or []
        include = ((item.get("conditions") or {}).get("users") or {}).get("includeGroups") or []
        normalized_policies[name] = Policy(
            state=_string(item, "state", f"policy {name}"),
            grant=frozenset(_string_list(controls, f"policy {name} grant")),
            include_groups=frozenset(_string_list(include, f"policy {name} groups")),
        )

    return State(
        groups=normalized_groups,
        rules=normalized_rules,
        apps=normalized_apps,
        policies=normalized_policies,
    )


def _record(
    findings: list[Finding],
    severity: str,
    kind: str,
    path: str,
    desired: str,
    live: str,
) -> None:
    findings.append(Finding(severity, kind, path, desired, live))


def _diff_named(
    findings: list[Finding],
    prefix: str,
    desired: dict[str, Any],
    live: dict[str, Any],
    missing_severity: str,
    extra_severity: str,
) -> list[str]:
    for name in sorted(set(desired) - set(live)):
        _record(findings, missing_severity, "missing", f"{prefix}/{name}", "present", "absent")
    for name in sorted(set(live) - set(desired)):
        _record(findings, extra_severity, "extra", f"{prefix}/{name}", "absent", "present")
    return sorted(set(desired) & set(live))


def _diff_text(
    findings: list[Finding],
    path: str,
    desired: str,
    live: str,
    severity: str,
) -> None:
    if desired != live:
        _record(findings, severity, "changed", path, desired, live)


def _diff_members(
    findings: list[Finding],
    path: str,
    desired: frozenset[str],
    live: frozenset[str],
    missing_severity: str,
    extra_severity: str,
) -> None:
    for name in sorted(desired - live):
        _record(findings, missing_severity, "missing", f"{path}/{name}", "assigned", "absent")
    for name in sorted(live - desired):
        _record(findings, extra_severity, "extra", f"{path}/{name}", "absent", "assigned")


def compare(desired: State, live: State) -> list[Finding]:
    findings: list[Finding] = []

    for name in _diff_named(findings, "groups", desired.groups, live.groups, "high", "low"):
        _diff_text(
            findings,
            f"groups/{name}/description",
            desired.groups[name].description,
            live.groups[name].description,
            "low",
        )

    for name in _diff_named(findings, "rules", desired.rules, live.rules, "high", "medium"):
        wanted = desired.rules[name]
        found = live.rules[name]
        _diff_text(findings, f"rules/{name}/group", wanted.group, found.group, "high")
        _diff_text(
            findings, f"rules/{name}/expression", wanted.expression, found.expression, "high"
        )
        _diff_text(findings, f"rules/{name}/status", wanted.status, found.status, "high")

    for name in _diff_named(findings, "apps", desired.apps, live.apps, "high", "medium"):
        wanted = desired.apps[name]
        found = live.apps[name]
        _diff_text(findings, f"apps/{name}/sign_on", wanted.sign_on, found.sign_on, "high")
        _diff_text(findings, f"apps/{name}/status", wanted.status, found.status, "high")
        _diff_text(findings, f"apps/{name}/audience", wanted.audience, found.audience, "high")
        _diff_members(
            findings,
            f"apps/{name}/assignments",
            wanted.assignments,
            found.assignments,
            "high",
            "medium",
        )

    for name in _diff_named(
        findings, "policies", desired.policies, live.policies, "high", "medium"
    ):
        wanted = desired.policies[name]
        found = live.policies[name]
        _diff_text(findings, f"policies/{name}/state", wanted.state, found.state, "high")
        _diff_members(
            findings, f"policies/{name}/grant", wanted.grant, found.grant, "high", "medium"
        )
        _diff_members(
            findings,
            f"policies/{name}/include_groups",
            wanted.include_groups,
            found.include_groups,
            "high",
            "medium",
        )

    return sorted(findings, key=lambda item: (SEVERITY_RANK[item.severity], item.path, item.kind))


def summarize(findings: list[Finding]) -> dict[str, int]:
    summary = {"total": len(findings), "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        summary[finding.severity] += 1
    return summary


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_markdown(findings: list[Finding], desired: Path, live: Path) -> str:
    summary = summarize(findings)
    lines = [
        "# Drift report",
        "",
        f"Desired: `{desired}`",
        f"Live: `{live}`",
        (
            f"Findings: {summary['total']} "
            f"(high {summary['high']}, medium {summary['medium']}, low {summary['low']})"
        ),
        "",
    ]
    if not findings:
        lines.append("No drift.")
        lines.append("")
        return "\n".join(lines)

    lines.extend(
        [
            "| Severity | Kind | Path | Desired | Live |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for finding in findings:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(finding.severity),
                    _cell(finding.kind),
                    _cell(finding.path),
                    _cell(finding.desired),
                    _cell(finding.live),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def render_json(findings: list[Finding], desired: Path, live: Path) -> str:
    payload = {
        "desired": str(desired),
        "live": str(live),
        "summary": summarize(findings),
        "findings": [finding.as_dict() for finding in findings],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare desired identity state to a live export.")
    parser.add_argument("--desired", required=True, type=Path, help="Desired-state YAML")
    parser.add_argument("--live", required=True, type=Path, help="Live export JSON")
    parser.add_argument("--markdown", type=Path, help="Write the markdown report here")
    parser.add_argument("--json", dest="json_path", type=Path, help="Write the JSON report here")
    parser.add_argument(
        "--exit-zero",
        action="store_true",
        help="Return 0 even when drift is found. Demo use.",
    )
    parser.add_argument("--quiet", action="store_true", help="Do not print the markdown report")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        desired_doc = load_yaml(args.desired)
        live_doc = load_json(args.live)
        findings = compare(
            normalize_desired(desired_doc, args.desired),
            normalize_live(live_doc, args.live),
        )
    except DriftError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    markdown = render_markdown(findings, args.desired, args.live)
    payload = render_json(findings, args.desired, args.live)
    if args.markdown:
        write_report(args.markdown, markdown)
    if args.json_path:
        write_report(args.json_path, payload)
    if not args.quiet:
        print(markdown, end="" if markdown.endswith("\n") else "\n")
    if findings and not args.exit_zero:
        return 1
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
