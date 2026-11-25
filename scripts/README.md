# Admin script example

`preview_group_changes.py` and `Preview-GroupChanges.ps1` are the same small tool in two languages. They compare a desired membership file to a directory export and print adds and removes.

Both default to dry-run. Nothing is written unless you pass the apply flag and an output path. The apply flag writes a new local JSON directory. It does not call Okta or Graph. Swap the load and save functions if you later point a copy of this script at an API, and keep dry-run as the default when you do.

## Python

```bash
python3 scripts/preview_group_changes.py \
  --desired scripts/samples/desired-groups.json \
  --export scripts/samples/directory-export.json \
  --log-file reports/preview.log

python3 scripts/preview_group_changes.py \
  --desired scripts/samples/desired-groups.json \
  --export scripts/samples/directory-export.json \
  --apply \
  --output reports/group-changes.json
```

## PowerShell

```powershell
pwsh scripts/Preview-GroupChanges.ps1 `
  -DesiredPath scripts/samples/desired-groups.json `
  -ExportPath scripts/samples/directory-export.json `
  -LogPath reports/preview-ps.log

pwsh scripts/Preview-GroupChanges.ps1 `
  -DesiredPath scripts/samples/desired-groups.json `
  -ExportPath scripts/samples/directory-export.json `
  -Apply `
  -OutputPath reports/group-changes.json
```

Groups that exist only in the export are reported as unmanaged and left in place. Groups that exist only in the desired file are created in the written document when you apply.

The sample files use `@lab.example.test` addresses. They are fixtures, not people.
