from pathlib import Path

import pytest
from helpers import ROOT, drift

DESIRED = ROOT / "tools" / "drift" / "samples" / "desired-state.yaml"
LIVE = ROOT / "tools" / "drift" / "samples" / "live-export.json"

EXPECTED_PATHS = {
    "groups/lab-contractors",
    "groups/lab-legacy",
    "groups/lab-readers/description",
    "rules/engineers-by-department/status",
    "apps/lab-portal/assignments/lab-engineers",
    "apps/lab-portal/assignments/lab-legacy",
    "policies/mfa-lab-admins/state",
}


def test_sample_has_the_deliberate_drift():
    findings = drift.compare(
        drift.normalize_desired(drift.load_yaml(DESIRED), DESIRED),
        drift.normalize_live(drift.load_json(LIVE), LIVE),
    )
    assert {item.path for item in findings} == EXPECTED_PATHS
    by_path = {item.path: item for item in findings}
    assert by_path["policies/mfa-lab-admins/state"].desired == "enabledForReportingButNotEnforced"
    assert by_path["policies/mfa-lab-admins/state"].live == "disabled"
    assert by_path["policies/mfa-lab-admins/state"].severity == "high"
    assert by_path["rules/engineers-by-department/status"].live == "INACTIVE"
    assert by_path["groups/lab-readers/description"].severity == "low"
    summary = drift.summarize(findings)
    assert summary == {"total": 7, "high": 4, "medium": 1, "low": 2}


def test_identical_state_has_no_drift():
    state = drift.normalize_desired(drift.load_yaml(DESIRED), DESIRED)
    assert drift.compare(state, state) == []


def test_cli_writes_markdown_and_json(tmp_path: Path):
    markdown = tmp_path / "drift.md"
    payload = tmp_path / "drift.json"
    code = drift.run(
        [
            "--desired",
            str(DESIRED),
            "--live",
            str(LIVE),
            "--markdown",
            str(markdown),
            "--json",
            str(payload),
            "--quiet",
        ]
    )
    assert code == 1
    assert "policies/mfa-lab-admins/state" in markdown.read_text(encoding="utf-8")
    text = payload.read_text(encoding="utf-8")
    assert '"total": 7' in text
    assert '"severity": "high"' in text


def test_exit_zero_flag_keeps_demo_green():
    assert (
        drift.run(["--desired", str(DESIRED), "--live", str(LIVE), "--quiet", "--exit-zero"]) == 0
    )


def test_missing_file_is_a_usage_error(tmp_path: Path):
    assert (
        drift.run(["--desired", str(tmp_path / "missing.yaml"), "--live", str(LIVE), "--quiet"])
        == 2
    )


def test_duplicate_desired_name_is_rejected(tmp_path: Path):
    path = tmp_path / "desired.yaml"
    path.write_text(
        "\n".join(
            [
                "version: 1",
                "groups:",
                "  - name: lab-a",
                "    description: one",
                "  - name: lab-a",
                "    description: two",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(drift.DriftError, match="duplicate"):
        drift.normalize_desired(drift.load_yaml(path), path)
