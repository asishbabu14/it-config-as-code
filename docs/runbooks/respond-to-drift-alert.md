# Responding to a drift alert

A drift alert means the configuration in git and something else disagree. Find out which check fired before you change code or a tenant.

## Which check fired

| Signal | Meaning |
| --- | --- |
| Nightly workflow "Drift plan" failed on `terraform plan -detailed-exitcode` | Terraform state and the configuration differ, or the plan errored |
| `tools/drift/checker.py` exited 1 | The desired-state YAML and the JSON export differ |
| `make demo` printed a drift table | That is the committed mock. It is supposed to drift. It is not an incident |

`make demo` passes `--exit-zero` so the mock does not fail the command. The findings are still real output from the sample files.

## Offline checker

1. Read `reports/drift.md` or the command output.
2. Each row is `missing`, `extra`, or `changed`, with a path such as `policies/mfa-lab-admins/state`.
3. Decide whether git or the export is right.
   - Git is right: fix the tenant (or the export, if the export is wrong) and rerun the checker.
   - The export is right: edit the desired-state YAML in a pull request so the next run is clean.
4. Do not silence the row by deleting the comparison. The sample mock is the only export that should stay drifted, and it lives in `tools/drift/samples/`.

The sample's deliberate drift is documented by the tests in `tests/test_drift.py`. If you change the sample, update the test in the same pull request.

## Terraform plan on a schedule

The nightly workflow skips itself when `OKTA_ORG_NAME` and `OKTA_API_TOKEN`, or `ARM_TENANT_ID`, `ARM_CLIENT_ID`, and `ARM_CLIENT_SECRET`, are unset.

When the secrets exist, the workflow runs:

```bash
terraform plan -detailed-exitcode -input=false -no-color
```

Exit codes from Terraform:

| Code | Meaning |
| --- | --- |
| 0 | No changes |
| 1 | Error. Read the log. Often a token, a permission, or a provider outage |
| 2 | Changes. State and config differ |

A GitHub-hosted runner starts with no state file. Against empty state, exit code 2 lists every resource as a create. That is not tenant drift. Before you treat a red nightly run as drift:

1. Confirm `terraform init` used the same backend you applied with. This repo defaults to local state. A remote backend is optional and is not wired in.
2. If the log is a full create, you need the real state, not a code change.
3. If the log is a small update or destroy, someone changed the tenant or the code outside a reviewed apply. Open a pull request that either adopts the live value or re-applies the code.

The workflow never runs `terraform apply`. Re-applying is a workstation step, after a pull request, using [change control](../change-control.md).

## While you investigate

Leave the Entra policy in report-only unless the drift is specifically "someone enforced it". If a console edit turned the policy on, the next apply of this repo puts it back to report-only. Decide in a pull request whether that is what you want, then apply.
