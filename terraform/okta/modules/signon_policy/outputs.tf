output "policy_id" {
  description = "Id of the application sign-on policy."
  value       = okta_app_signon_policy.this.id
}

output "rule_id" {
  description = "Id of the allow rule."
  value       = okta_app_signon_policy_rule.allow.id
}
