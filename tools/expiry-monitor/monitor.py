#!/usr/bin/env python3
"""Warn when lab certificates or domain names are close to expiry.

The inventory is YAML. Certificates are read from PEM files, SAML metadata
XML, an explicit timestamp, or an optional live TLS connection. Domain dates
come from the inventory itself. Nothing here is a trust check: the live TLS
read disables certificate verification so an expired or privately signed lab
certificate can still be dated.

Thresholds, measured in whole days remaining:
  60  notice
  30  warning
   7  critical
  <0  expired

Exit codes:
  0  no critical, expired, or error rows
  1  at least one of those rows
  2  usage or inventory error
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import socket
import ssl
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from cryptography import x509

STATUS_RANK = {"expired": 0, "critical": 1, "error": 2, "warning": 3, "notice": 4, "ok": 5}
CRITICAL_STATUSES = {"expired", "critical", "error"}
KINDS = {"saml_signing", "ssl", "apple_push", "wifi"}


class InventoryError(Exception):
    """The inventory file or a certificate it points at is unusable."""


@dataclass(frozen=True)
class Item:
    name: str
    kind: str
    status: str
    days_left: int | None
    expires: str | None
    source: str
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_time(value: object, label: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day, tzinfo=UTC)
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            if len(text) == 10:
                parsed = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=UTC)
            else:
                parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise InventoryError(f"{label} is not a timestamp: {value}") from exc
    else:
        raise InventoryError(f"{label} is not a timestamp")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def days_until(expires: datetime, now: datetime) -> int:
    delta = expires.astimezone(UTC) - now.astimezone(UTC)
    return math.floor(delta.total_seconds() / 86400)


def classify(days_left: int) -> str:
    if days_left < 0:
        return "expired"
    if days_left <= 7:
        return "critical"
    if days_left <= 30:
        return "warning"
    if days_left <= 60:
        return "notice"
    return "ok"


def format_time(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_pem_expiry(path: Path) -> datetime:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise InventoryError(f"cannot read {path}: {exc}") from exc
    try:
        certificate = x509.load_pem_x509_certificate(data)
    except ValueError as exc:
        raise InventoryError(f"{path} is not a PEM certificate: {exc}") from exc
    return certificate.not_valid_after_utc


def load_metadata_expiry(path: Path) -> datetime:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise InventoryError(f"cannot read metadata {path}: {exc}") from exc
    expiries: list[datetime] = []
    for element in root.iter():
        if not element.tag.endswith("X509Certificate") or not element.text:
            continue
        try:
            der = base64.b64decode("".join(element.text.split()), validate=True)
            certificate = x509.load_der_x509_certificate(der)
        except ValueError as exc:
            raise InventoryError(f"bad X509Certificate in {path}: {exc}") from exc
        expiries.append(certificate.not_valid_after_utc)
    if not expiries:
        raise InventoryError(f"no X509Certificate in {path}")
    return min(expiries)


def read_tls_expiry(host: str, port: int, timeout: float) -> datetime:
    """Return the not-after time of the leaf certificate presented by host.

    Verification is off so a lab certificate that is self-signed or already
    expired can still be dated. Do not use this as a trust decision.
    """

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with (
            socket.create_connection((host, port), timeout=timeout) as raw,
            context.wrap_socket(raw, server_hostname=host) as tls,
        ):
            der = tls.getpeercert(binary_form=True)
    except OSError as exc:
        raise InventoryError(f"TLS connection to {host}:{port} failed: {exc}") from exc
    if not der:
        raise InventoryError(f"no certificate from {host}:{port}")
    return x509.load_der_x509_certificate(der).not_valid_after_utc


def _resolve(inventory_path: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = inventory_path.parent / path
    return path


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InventoryError(f"{label} must be a mapping")
    return value


def _items(document: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = document.get(key) or []
    if not isinstance(raw, list):
        raise InventoryError(f"{key} must be a list")
    return [_mapping(item, key) for item in raw]


def evaluate_certificate(
    inventory_path: Path,
    spec: dict[str, Any],
    now: datetime,
    timeout: float,
) -> Item:
    name = spec.get("name")
    kind = spec.get("kind")
    if not isinstance(name, str) or not name:
        raise InventoryError("each certificate needs a name")
    if kind not in KINDS:
        raise InventoryError(f"{name}: kind must be one of {', '.join(sorted(KINDS))}")

    live_check = bool(spec.get("live_check", False))
    if live_check:
        host = spec.get("host")
        port = spec.get("port", 443)
        if not isinstance(host, str) or not host:
            raise InventoryError(f"{name}: live_check requires host")
        if not isinstance(port, int):
            raise InventoryError(f"{name}: port must be an integer")
        try:
            expires = read_tls_expiry(host, port, timeout)
        except InventoryError as exc:
            return Item(name, kind, "error", None, None, "tls", str(exc))
        return _dated(name, kind, expires, now, "tls")

    if "pem" in spec:
        return _dated(
            name, kind, load_pem_expiry(_resolve(inventory_path, str(spec["pem"]))), now, "pem"
        )
    if "metadata" in spec:
        expires = load_metadata_expiry(_resolve(inventory_path, str(spec["metadata"])))
        return _dated(name, kind, expires, now, "metadata")
    if "not_after" in spec:
        return _dated(name, kind, parse_time(spec["not_after"], f"{name} not_after"), now, "date")
    raise InventoryError(f"{name}: set pem, metadata, not_after, or live_check")


def evaluate_domain(spec: dict[str, Any], now: datetime) -> Item:
    name = spec.get("name")
    if not isinstance(name, str) or not name:
        raise InventoryError("each domain needs a name")
    if "expires_on" not in spec:
        raise InventoryError(f"{name}: expires_on is required")
    return _dated(name, "domain", parse_time(spec["expires_on"], f"{name} expires_on"), now, "date")


def _dated(name: str, kind: str, expires: datetime, now: datetime, source: str) -> Item:
    remaining = days_until(expires, now)
    status = classify(remaining)
    detail = _detail(status, remaining)
    return Item(name, kind, status, remaining, format_time(expires), source, detail)


def _detail(status: str, days_left: int) -> str:
    if status == "expired":
        return f"expired {abs(days_left)} days ago"
    if status == "critical":
        return f"{days_left} days left, within 7"
    if status == "warning":
        return f"{days_left} days left, within 30"
    if status == "notice":
        return f"{days_left} days left, within 60"
    return f"{days_left} days left"


def load_inventory(path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InventoryError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise InventoryError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise InventoryError(f"{path} must contain a mapping")
    return document


def evaluate(inventory_path: Path, now: datetime, timeout: float = 5.0) -> list[Item]:
    document = load_inventory(inventory_path)
    items = [
        evaluate_certificate(inventory_path, spec, now, timeout)
        for spec in _items(document, "certificates")
    ]
    items.extend(evaluate_domain(spec, now) for spec in _items(document, "domains"))
    return sorted(items, key=lambda item: (STATUS_RANK[item.status], item.name))


def summarize(items: list[Item]) -> dict[str, int]:
    summary = {status: 0 for status in STATUS_RANK}
    for item in items:
        summary[item.status] += 1
    summary["action_needed"] = sum(summary[status] for status in CRITICAL_STATUSES)
    return summary


def _cell(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(items: list[Item], inventory: Path, now: datetime) -> str:
    summary = summarize(items)
    lines = [
        "# Certificate and domain expiry",
        "",
        f"Inventory: `{inventory}`",
        f"As of: {format_time(now)}",
        (
            "Action needed: {action} (critical {critical}, expired {expired}, error {error}). "
            "Warning: {warning}. Notice: {notice}. Ok: {ok}."
        ).format(
            action=summary["action_needed"],
            critical=summary["critical"],
            expired=summary["expired"],
            error=summary["error"],
            warning=summary["warning"],
            notice=summary["notice"],
            ok=summary["ok"],
        ),
        "",
        "| Status | Kind | Name | Days | Expires | Source | Detail |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(item.status),
                    _cell(item.kind),
                    _cell(item.name),
                    _cell(item.days_left),
                    _cell(item.expires),
                    _cell(item.source),
                    _cell(item.detail),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def render_json(items: list[Item], inventory: Path, now: datetime) -> str:
    payload = {
        "as_of": format_time(now),
        "inventory": str(inventory),
        "items": [item.as_dict() for item in items],
        "summary": summarize(items),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    return parse_time(value, "--now")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report certificate and domain expiry.")
    parser.add_argument("--inventory", required=True, type=Path, help="Inventory YAML")
    parser.add_argument("--now", help="Clock override, ISO-8601. Defaults to the current time.")
    parser.add_argument("--markdown", type=Path, help="Write the markdown report here")
    parser.add_argument("--json", dest="json_path", type=Path, help="Write the JSON report here")
    parser.add_argument("--timeout", type=float, default=5.0, help="TLS timeout in seconds")
    parser.add_argument(
        "--exit-zero",
        action="store_true",
        help="Return 0 even when critical rows are present. Demo use.",
    )
    parser.add_argument("--quiet", action="store_true", help="Do not print the markdown report")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        now = parse_now(args.now)
        items = evaluate(args.inventory, now, timeout=args.timeout)
    except InventoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    markdown = render_markdown(items, args.inventory, now)
    payload = render_json(items, args.inventory, now)
    if args.markdown:
        write_report(args.markdown, markdown)
    if args.json_path:
        write_report(args.json_path, payload)
    if not args.quiet:
        print(markdown, end="" if markdown.endswith("\n") else "\n")
    if summarize(items)["action_needed"] and not args.exit_zero:
        return 1
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
