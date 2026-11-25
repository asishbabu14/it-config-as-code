# IT configuration as code

Personal lab for Asish Babu. Identity configuration for Okta and Entra ID, reviewed in pull requests, with drift detection and certificate and domain expiry checks.

This is lab work. The sample tenants, certificates, and directory exports are fixtures. Nothing here is a claim about a production environment.

## What this is

- Terraform modules for an Okta lab (groups, group rules, a SAML app, assignments, and a sign-on policy) and an Entra lab (groups, a conditional access policy fixed to report-only, and an app registration)
- GitHub Actions checks on every pull request: `terraform fmt`, `validate`, `tflint`, and a Trivy config scan
- A plan, and a plan comment, only when repository secrets for a real tenant are present. Otherwise those steps skip and the workflow stays green
- A nightly `terraform plan -detailed-exitcode` with the same secret gate
- An offline drift checker that diffs desired-state YAML against a mock JSON export and writes markdown and JSON
- An expiry monitor for SAML signing certificates, SSL certificates, an Apple Push certificate, an 802.1X certificate, and domain names
- A small admin script in Python and PowerShell with a dry-run default

Apply is not automated. Merging to `main` does not change a tenant.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make demo
make test
make lint
```

`make demo` is offline. It runs the drift checker against the sample that contains deliberate drift, then the expiry monitor with the clock frozen at `2028-04-01`. Reports land in `reports/`, which is gitignored.

Terraform validate needs the CLI and no credentials:

```bash
terraform -chdir=terraform/okta/environments/lab init -backend=false
terraform -chdir=terraform/okta/environments/lab validate
terraform -chdir=terraform/entra/environments/lab init -backend=false
terraform -chdir=terraform/entra/environments/lab validate
```

Optional real-tenant setup: [docs/okta-dev-setup.md](docs/okta-dev-setup.md) and [docs/entra-setup.md](docs/entra-setup.md).

## Pull request workflow

1. Branch from `main` and open a pull request. The template asks for change, risk, rollback, and test. [docs/change-control.md](docs/change-control.md) is the longer version.
2. `.github/CODEOWNERS` requests a review.
3. CI runs the Python tests and the Terraform checks above. `terraform plan` runs for Okta only when `OKTA_ORG_NAME` and `OKTA_API_TOKEN` are set, and for Entra only when `ARM_TENANT_ID`, `ARM_CLIENT_ID`, and `ARM_CLIENT_SECRET` are set. A missing secret skips that plan. It does not fail the pull request.
4. When a plan runs, the plan comment step posts or updates a comment on the pull request.
5. After merge, apply from a workstation if you have a tenant. CI never runs `terraform apply`.

Two schedules run on `main`:

| Workflow | When | What |
| --- | --- | --- |
| Drift plan | 07:15 UTC | `terraform plan -detailed-exitcode`, skipped when secrets are absent. Exit code 2 fails the run |
| Expiry monitor | 07:30 UTC | Reads `tools/expiry-monitor/inventory/lab.yaml` on the real clock and fails on critical, expired, or error rows |

## Demo

```bash
make demo
```

![Terminal recording of make demo](docs/images/demo.gif)

The drift table is the committed mock: a missing group, a stale description, an inactive rule, a missing app assignment, an extra assignment, and a conditional access policy that was turned off. The expiry table uses the same inventory as the nightly run, with the clock moved to `2028-04-01` so you can see notice, warning, critical, and expired together. On today's date those fixture certificates are still healthy, which is why the nightly run stays green until the dates get close.

## Mocked and real

| Piece | Mocked, offline | Real, optional |
| --- | --- | --- |
| Drift checker live side | `tools/drift/samples/live-export.json` | A JSON file you produce in the same shape. The checker never logs in |
| Drift, Terraform | Not used by `make demo` | Nightly and pull request plans, only with secrets. Local state on a runner is empty unless you add a backend |
| Certificates | Generated PEM and metadata in `tools/expiry-monitor/fixtures/certs/` | Point the inventory at files from a tenant, or set `live_check: true` on an SSL row |
| Apple Push and domains | Dates in the inventory | Replace `not_after` and `expires_on` when you track a real certificate or name |
| Admin script | `scripts/samples/*.json` | `--apply` still only writes a local file |
| Okta and Entra resources | `terraform validate` uses the provider schema only | `plan` and `apply` when you export a token or client secret |

The live TLS check does not validate trust. It reads the expiry from whatever certificate the host presents. The sample inventory leaves it off.

## Layout

```
terraform/okta/          groups, rules, SAML app, sign-on policy
terraform/entra/         groups, report-only conditional access, app registration
tools/drift/             offline desired-state diff
tools/expiry-monitor/    certificate and domain dates
scripts/                 Python and PowerShell dry-run example
docs/                    architecture, change control, runbooks, setup
.github/                 workflows, CODEOWNERS, pull request template
```

Runbooks:

- [Rolling back a bad Terraform apply](docs/runbooks/rollback-terraform-apply.md)
- [Rotating a SAML signing certificate](docs/runbooks/rotate-saml-signing-cert.md)
- [Responding to a drift alert](docs/runbooks/respond-to-drift-alert.md)
- [Renewing an Apple Push certificate](docs/runbooks/renew-apple-push-cert.md)

Architecture diagram and the normalized drift model: [docs/architecture.md](docs/architecture.md).

## License

[MIT](LICENSE)
