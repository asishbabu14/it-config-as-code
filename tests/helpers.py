"""Load the lab tools, which are scripts rather than an installed package."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


drift = load("drift_checker", "tools/drift/checker.py")
expiry = load("expiry_monitor", "tools/expiry-monitor/monitor.py")
preview = load("preview_group_changes", "scripts/preview_group_changes.py")
