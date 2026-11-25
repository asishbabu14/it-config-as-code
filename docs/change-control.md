# Change control

Lab changes land through a pull request. The point is a reviewable diff, a green check, and a written rollback, even when the tenant on the other side is a personal dev org.

## 1. Branch

Create a branch from `main`. Keep the change small enough that the plan is readable. A group description and a new conditional access policy do not belong in the same pull request if you can split them.

## 2. Open a pull request

The template asks for four sections:

- Change: what the diff does
- Risk: who could lose access, gain access, or fail sign-on if this is applied
- Rollback: how to get back, usually the previous commit plus the rollback runbook
- Test: commands you ran, and what a reviewer can run

`.github/CODEOWNERS` requests a review from the repository owner.

## 3. Checks

Every pull request runs:

- `terraform fmt -check`
- `terraform validate` for the Okta and Entra roots
- `tflint`
- `trivy config` on `terraform/`
- `make lint` and `make test`

`terraform plan` runs only when the matching secrets are set. When they are missing, that step is skipped and the workflow stays green. When they are set, a later step comments the plan on the pull request. Plans are not applies. A plan that shows changes does not fail the pull request. A plan that errors does.

## 4. Review

Read the plan, not only the HCL. For the Entra stack, confirm the conditional access resource is still `enabledForReportingButNotEnforced` unless the pull request is explicitly about enforcement. For Okta, confirm group assignments and the sign-on policy still match.

## 5. Merge, then apply by hand

Merging updates `main`. It does not change a tenant. From the stack directory, on a workstation that has the token or client secret:

```bash
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

If the plan does not match what was reviewed, stop.

## 6. After apply

The nightly drift workflow runs `terraform plan -detailed-exitcode` when secrets exist. The expiry workflow reads the inventory. Neither workflow applies.

## Emergency

If an apply already caused a bad sign-on or membership change, use [Rolling back a bad Terraform apply](runbooks/rollback-terraform-apply.md). Do not delete the state file to "start over".
