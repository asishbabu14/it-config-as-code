# Okta lab stack

Manages a personal lab directory in Okta:

- Groups (`lab-engineers`, `lab-readers`, `lab-admins`)
- Group rules that place people into those groups from the department attribute
- A custom SAML app, `lab-portal`, with signed responses and assertions
- An application sign-on policy whose catch-all rule denies, plus an allow rule that asks for a password and another factor
- Group assignments that place the app on the dashboard for engineers and readers

The sign-on policy resources require an Identity Engine org. A Classic org can still validate this configuration, and apply will fail on those two resources until the org is Identity Engine. See [okta-dev-setup.md](../../docs/okta-dev-setup.md).

## Layout

```
environments/lab/     root module, tfvars example, provider
modules/groups/
modules/group_rules/
modules/signon_policy/
modules/saml_app/
```

`environments/lab` is the only root module. Modules declare the provider source and leave the version pin to the root.

## Offline check

```bash
cd terraform/okta/environments/lab
terraform init -backend=false
terraform validate
```

`validate` does not call Okta and does not need a token.

## Plan against a dev org

```bash
cp terraform.tfvars.example terraform.tfvars
# edit okta_org_name
export TF_VAR_okta_api_token="..."
terraform init
terraform plan -var-file=terraform.tfvars
```

Apply stays on your workstation. CI plans only when `OKTA_ORG_NAME` and `OKTA_API_TOKEN` are present, and it never applies.

State is local unless you add a backend. A GitHub-hosted runner starts with empty state, so a plan there lists every resource as a create until you point init at the state you applied from. See the drift runbook.
