output "policy_id" {
  description = "Object id of the report-only conditional access policy."
  value       = azuread_conditional_access_policy.this.id
}
