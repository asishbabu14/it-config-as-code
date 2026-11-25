# Rolling back a bad Terraform apply

Use this when an apply changed a lab tenant and you want the previous configuration back.

CI does not apply, so the apply you are undoing happened on a workstation. The state file from that apply is the one you must keep using. A fresh clone with empty state will try to create everything again.

## 1. Stop

Do not run a second apply while you are still guessing. Save the command output from the bad apply.

## 2. Put the git tree back

```bash
git checkout <previous-good-commit>
```

Or revert the pull request on `main` and pull that revert. Use the same commit the state was applied from, plus your revert, so the next plan is the reverse of the bad change.

## 3. Plan against the same state

```bash
cd terraform/okta/environments/lab   # or terraform/entra/environments/lab
terraform init
terraform plan -var-file=terraform.tfvars
```

Read the plan. You want updates and destroys that undo the bad apply, not a full create of every resource. If you see a full create, you are on empty state. Point `terraform init` at the state you applied with, then plan again.

## 4. Apply the reverse plan

```bash
terraform apply -var-file=terraform.tfvars
```

Watch sign-on for the lab app after the apply. A sign-on policy change and a group assignment change both affect who can open `lab-portal`.

## 5. Record it

Open a pull request with the revert if you rolled back by checking out an old commit locally. The history should show the bad change and the undo.

## Do not

- Do not delete `terraform.tfstate` to force a clean plan.
- Do not flip the Entra policy to `disabled` in the console and leave the code saying report-only. The next apply will put the code back, and the nightly plan will shout until you do.
- Do not run apply from a GitHub Actions workflow in this repo. There is no apply workflow, and adding one is a separate decision.
