# Entra lab stack

Manages a personal lab tenant slice with the `azuread` provider:

- Security groups (`lab-admins`, `lab-engineers`, `lab-readers`)
- A conditional access policy fixed to report-only mode (`enabledForReportingButNotEnforced`) that would require MFA for `lab-admins`
- An app registration for `lab-portal` in a single tenant, with delegated User.Read, plus its service principal

The policy state is a literal in `modules/conditional_access`. Promoting it to enforced means editing that module, so the change is obvious in review.

## Layout

```
environments/lab/              root module, tfvars example, provider
modules/groups/
modules/conditional_access/
modules/app_registration/
```

## Offline check

```bash
cd terraform/entra/environments/lab
terraform init -backend=false
terraform validate
```

`validate` does not call Graph and does not need a secret.

## Plan against a tenant

Follow [entra-setup.md](../../docs/entra-setup.md), then:

```bash
cp terraform.tfvars.example terraform.tfvars
# edit tenant_id and client_id
export TF_VAR_client_secret="..."
terraform init
terraform plan -var-file=terraform.tfvars
```

Apply stays on your workstation. CI plans only when `ARM_TENANT_ID`, `ARM_CLIENT_ID`, and `ARM_CLIENT_SECRET` are present, and it never applies.
