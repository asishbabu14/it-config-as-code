# Rotating a SAML signing certificate

Use this when the lab portal SAML signing certificate is inside the 60 day window, or when the expiry monitor reports it as critical.

The Okta app resource can mint a new signing key when `key_name` and `key_years_valid` change together. A new `key_name` means a new key. This lab ships without those arguments, so the provider uses Okta's default certificate until you opt in.

## 1. See the current date

```bash
python3 tools/expiry-monitor/monitor.py \
  --inventory tools/expiry-monitor/inventory/lab.yaml
```

For a real app, point a PEM or the metadata XML at the certificate Okta is publishing. The sample files under `tools/expiry-monitor/fixtures/certs/` are generated lab material, not a tenant certificate.

## 2. Add the new key in a pull request

In `terraform/okta/modules/saml_app`, set both arguments on `okta_app_saml.this`:

```hcl
key_name        = "lab-portal-2028"
key_years_valid = 2
```

Open a pull request. The plan should show a key change on the app, not a destroy of the app. If the plan wants to replace the application, stop and check you did not rename `label` or other force-new arguments in the same edit.

## 3. Apply, then update the relying party

After apply, download the new metadata from the `metadata_url` output. Give that metadata to the lab portal (the relying party) and confirm it accepts the new certificate before anyone removes the old one.

Okta can keep the previous key for a while. Leave it in place until the relying party has switched and a test sign-on works.

## 4. Update the inventory

Replace the PEM or metadata path in `tools/expiry-monitor/inventory/lab.yaml` with the new certificate, in the same pull request as the Terraform change or in a follow-up. The monitor should show the new date on the next run.

## 5. Retire the old key

When the relying party no longer needs the old certificate, retire it in Okta if it is still published. Do that in a separate pull request if it is represented in Terraform, so the rollback of the retirement does not also roll back the new key.

## Rollback

If the new certificate breaks sign-on, put the relying party back on the previous metadata. Then revert the `key_name` change only if Okta will still serve the old key. If the old key is already gone, the rollback is "issue another key and update the relying party", not a git revert alone. Say that in the pull request before you apply.
