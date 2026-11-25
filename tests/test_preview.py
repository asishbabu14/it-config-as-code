import json
from pathlib import Path

from helpers import ROOT, preview

DESIRED = ROOT / "scripts" / "samples" / "desired-groups.json"
EXPORT = ROOT / "scripts" / "samples" / "directory-export.json"


def test_sample_plan_adds_removes_and_leaves_unmanaged():
    changes, unmanaged = preview.plan(preview.load_groups(DESIRED), preview.load_groups(EXPORT))
    assert unmanaged == ["lab-legacy"]
    assert len(changes) == 1
    change = changes[0]
    assert change.group == "lab-engineers"
    assert change.add == ("bea@lab.example.test",)
    assert change.remove == ("cy@lab.example.test",)


def test_apply_writes_sorted_directory_without_touching_the_export(tmp_path: Path):
    export = tmp_path / "export.json"
    export.write_text(EXPORT.read_text(encoding="utf-8"), encoding="utf-8")
    output = tmp_path / "out" / "directory.json"
    code = preview.run(
        [
            "--desired",
            str(DESIRED),
            "--export",
            str(export),
            "--apply",
            "--output",
            str(output),
            "--log-file",
            str(tmp_path / "preview.log"),
        ]
    )
    assert code == 0
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["groups"]["lab-engineers"] == [
        "ada@lab.example.test",
        "bea@lab.example.test",
    ]
    assert written["groups"]["lab-legacy"] == ["dee@lab.example.test"]
    assert "cy@lab.example.test" not in written["groups"]["lab-engineers"]
    assert json.loads(export.read_text(encoding="utf-8"))["groups"]["lab-engineers"] == [
        "ada@lab.example.test",
        "cy@lab.example.test",
    ]
    log = (tmp_path / "preview.log").read_text(encoding="utf-8")
    assert "add bea@lab.example.test to lab-engineers" in log
    assert "dry-run" not in log


def test_dry_run_does_not_write_output(tmp_path: Path):
    output = tmp_path / "should-not-exist.json"
    code = preview.run(
        ["--desired", str(DESIRED), "--export", str(EXPORT), "--output", str(output)]
    )
    assert code == 0
    assert not output.exists()


def test_apply_without_output_is_rejected():
    assert preview.run(["--desired", str(DESIRED), "--export", str(EXPORT), "--apply"]) == 2


def test_invalid_json_is_rejected(tmp_path: Path):
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert preview.run(["--desired", str(broken), "--export", str(EXPORT)]) == 2
