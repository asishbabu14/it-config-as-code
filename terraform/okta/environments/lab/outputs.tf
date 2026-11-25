output "group_ids" {
  description = "Okta group ids for the lab groups."
  value       = module.groups.group_ids
}

output "group_rule_ids" {
  description = "Okta group rule ids."
  value       = module.group_rules.rule_ids
}

output "signon_policy_id" {
  description = "Application sign-on policy id attached to the lab portal."
  value       = module.signon_policy.policy_id
}

output "app_id" {
  description = "Lab portal application id."
  value       = module.saml_app.app_id
}

output "metadata_url" {
  description = "SAML metadata URL for the lab portal."
  value       = module.saml_app.metadata_url
}
