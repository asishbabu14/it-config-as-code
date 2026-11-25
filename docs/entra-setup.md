# Optional Entra tenant

The Entra stack validates with no secret. A plan or apply needs a tenant you control and an app registration used only by Terraform. Skip this page if you only want the offline demo.

## 1. Terraform client

In the tenant:

1. Register an application, single tenant, named something you will recognize as the Terraform client. This is not the `lab-portal` app. `lab-portal` is created by the stack.
2. Add a client secret. Copy the value once.
3. Grant these application permissions, then grant admin consent:
   - `Group.ReadWrite.All`
   - `Application.ReadWrite.All`
   - `Policy.Read.All`
   - `Policy.ReadWrite.ConditionalAccess`

The conditional access permission is what lets the provider write the report-only policy. Without consent, plan fails on that resource.

## 2. Values

You need the tenant id, the Terraform client's application id, and the client secret.

```bash
export TF_VAR_client_secret="paste-the-secret"
```

Keep the secret out of `terraform.tfvars` and out of git.

For GitHub Actions, add repository secrets:

| Secret | Maps to |
| --- | --- |
| `ARM_TENANT_ID` | `TF_VAR_tenant_id` |
| `ARM_CLIENT_ID` | `TF_VAR_client_id` |
| `ARM_CLIENT_SECRET` | `TF_VAR_client_secret` |

The plan step runs only when all three are non-empty. Otherwise it is skipped and the workflow stays green.

## 3. Local plan

```bash
cd terraform/entra/environments/lab
cp terraform.tfvars.example terraform.tfvars
# replace tenant_id and client_id. Leave the secret in the environment.
export TF_VAR_client_secret="paste-the-secret"
terraform init
terraform plan -var-file=terraform.tfvars
```

The example file uses the nil UUID so it parses. Override both ids. A plan sent at the nil UUID will fail authentication, which is what you want from a placeholder.

## 4. Apply

```bash
terraform apply -var-file=terraform.tfvars
```

The first apply creates:

- Security groups `lab-admins`, `lab-engineers`, and `lab-readers`
- A conditional access policy `lab-admins-mfa-report-only` in report-only mode, scoped to `lab-admins`, that would require MFA
- An app registration `lab-portal` with delegated User.Read, and a service principal

Report-only means sign-in logs record what the policy would have done. It does not prompt anyone for MFA. The state value is hardcoded in the module. A pull request that changes it to `enabled` is the enforcement change, and it should say so in the risk section.

The app registration's owner is the Terraform client, from `azuread_client_config`.

## 5. State

The backend is local. Nightly drift detection on a runner only works if that runner can see the state you applied. Empty state produces a plan that creates every resource. See [Responding to a drift alert](runbooks/respond-to-drift-alert.md).

## 6. Remove the lab

```bash
terraform destroy -var-file=terraform.tfvars
```

Then delete the client secret, and the Terraform client app registration if you have no further use for it.
