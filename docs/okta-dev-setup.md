# Optional Okta dev org

The Okta stack validates, lints, and scans with no token. A plan or apply needs an org you control. This page is that optional path. Skip it if you only want the offline demo.

## 1. Org

Create a developer org from the Okta developer signup. The sign-on policy resources in this repo require Identity Engine. A Classic org will fail on `okta_app_signon_policy` and `okta_app_signon_policy_rule` at apply time. `terraform validate` still passes, because it only checks configuration shape.

The org subdomain is `okta_org_name`. The base URL is usually `okta.com` for a production-style org and `oktapreview.com` for a preview org. Use the host you actually sign in to.

## 2. Token

Create an API token that can manage groups, group rules, applications, and authentication policies. Store it outside the repo.

```bash
export TF_VAR_okta_api_token="paste-the-token"
```

Do not put the token in `terraform.tfvars` or in a pull request.

For GitHub Actions plan comments, add repository secrets:

| Secret | Example | Required for a plan |
| --- | --- | --- |
| `OKTA_ORG_NAME` | your subdomain | yes |
| `OKTA_API_TOKEN` | the token | yes |
| `OKTA_BASE_URL` | `okta.com` | no, defaults to `okta.com` |

The workflow maps those onto `TF_VAR_okta_org_name`, `TF_VAR_okta_api_token`, and `TF_VAR_okta_base_url`. If either required secret is empty, the Okta plan step is skipped.

## 3. Local plan

```bash
cd terraform/okta/environments/lab
cp terraform.tfvars.example terraform.tfvars
# edit okta_org_name in terraform.tfvars
export TF_VAR_okta_api_token="paste-the-token"
terraform init
terraform plan -var-file=terraform.tfvars
```

`terraform.tfvars` is gitignored. The example file is the reviewed lab shape: three groups, two rules, one SAML app, one sign-on policy.

## 4. Apply

```bash
terraform apply -var-file=terraform.tfvars
```

Apply from the workstation that holds the state. This repo's CI never applies. The nightly drift plan only matches a real tenant if that same state is available to the runner. With the default local backend, a runner has empty state and will plan a full create. See [Responding to a drift alert](runbooks/respond-to-drift-alert.md).

## 5. What the first apply creates

- Groups `lab-engineers`, `lab-readers`, and `lab-admins`
- Rules that assign Engineering and Research department values into the first two groups
- A sign-on policy named `lab-portal-signon` with a deny catch-all and an allow rule for engineers and readers (password plus another factor)
- A SAML app named `lab-portal` aimed at `https://lab.example.test`, assigned to those two groups

`lab.example.test` does not resolve. It is a placeholder audience so the app object exists. Point `sso_url`, `recipient`, `destination`, and `audience` at a relying party you run before you expect a browser sign-on to succeed.

## 6. If apply returns a feature error

The provider documents an error, "You do not have permission to access the feature you are requesting", for some SAML settings. That org needs the `ADVANCED_SSO` feature enabled. A dev org usually has it. If yours does not, drop the extra SAML arguments in a branch and plan again, rather than pasting a token into an issue.

## 7. Remove the lab

```bash
terraform destroy -var-file=terraform.tfvars
```

Then delete the API token in the Okta admin console.
