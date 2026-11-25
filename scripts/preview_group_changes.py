#!/usr/bin/env python3
"""Preview group membership changes against a local directory export.

This is a source-controlled admin script pattern: argument parsing, a dry-run
default, and a log. It reads JSON files only. `--apply` writes an updated
directory document to `--output`. It does not call Okta, Graph, or any other
network API.

Exit codes:
  0  plan computed (whether or not there were changes)
  2  usage or input error
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("preview_group_changes")


class ScriptError(Exception):
    """Input files could not be used."""


@dataclass(frozen=True)
class Change:
    group: str
    add: tuple[str, ...]
    remove: tuple[str, ...]


def load_groups(path: Path) -> dict[str, set[str]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScriptError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ScriptError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("groups"), dict):
        raise ScriptError(f"{path} must contain an object with a groups object")

    groups: dict[str, set[str]] = {}
    for name, members in document["groups"].items():
        if not isinstance(name, str) or not name:
            raise ScriptError(f"{path}: group names must be strings")
        if not isinstance(members, list) or not all(isinstance(member, str) for member in members):
            raise ScriptError(f"{path}: members of {name} must be a list of strings")
        groups[name] = set(members)
    return groups


def plan(desired: dict[str, set[str]], live: dict[str, set[str]]) -> tuple[list[Change], list[str]]:
    changes: list[Change] = []
    for name in sorted(desired):
        current = live.get(name, set())
        add = tuple(sorted(desired[name] - current))
        remove = tuple(sorted(current - desired[name]))
        if add or remove:
            changes.append(Change(name, add, remove))
    unmanaged = sorted(set(live) - set(desired))
    return changes, unmanaged


def apply_plan(live: dict[str, set[str]], changes: list[Change]) -> dict[str, list[str]]:
    updated = {name: set(members) for name, members in live.items()}
    for change in changes:
        bucket = updated.setdefault(change.group, set())
        bucket.difference_update(change.remove)
        bucket.update(change.add)
    return {name: sorted(members) for name, members in sorted(updated.items())}


def render_text(changes: list[Change], unmanaged: list[str], applied: bool) -> str:
    lines: list[str] = []
    if not changes:
        lines.append("No membership changes.")
    for change in changes:
        lines.append(f"{change.group}")
        for member in change.add:
            lines.append(f"  add {member}")
        for member in change.remove:
            lines.append(f"  remove {member}")
    for name in unmanaged:
        lines.append(f"unmanaged {name}")
    if applied:
        lines.append("wrote the updated directory")
    else:
        lines.append("dry-run: no file written")
    return "\n".join(lines) + "\n"


def configure_logging(verbose: bool, log_file: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview group membership changes on local JSON.")
    parser.add_argument("--desired", required=True, type=Path, help="Desired membership JSON")
    parser.add_argument("--export", required=True, type=Path, help="Directory export JSON")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the updated directory to --output. Omit this for a dry-run.",
    )
    parser.add_argument("--output", type=Path, help="Destination for --apply")
    parser.add_argument("--log-file", type=Path, help="Also write logs to this file")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose, args.log_file)
    if args.apply and args.output is None:
        print("error: --apply requires --output", file=sys.stderr)
        return 2
    try:
        desired = load_groups(args.desired)
        live = load_groups(args.export)
    except ScriptError as exc:
        logger.error("%s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 2

    changes, unmanaged = plan(desired, live)
    for change in changes:
        for member in change.add:
            logger.info("add %s to %s", member, change.group)
        for member in change.remove:
            logger.info("remove %s from %s", member, change.group)
    for name in unmanaged:
        logger.info("unmanaged group %s", name)
    if args.apply:
        updated = {"groups": apply_plan(live, changes)}
        assert args.output is not None
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        logger.info("wrote %s", args.output)
    else:
        logger.info("dry-run: no file written")
    print(render_text(changes, unmanaged, args.apply), end="")
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
