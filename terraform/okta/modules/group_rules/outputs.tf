output "rule_ids" {
  description = "Okta group rule ids keyed by the same keys as var.rules."
  value       = { for key, rule in okta_group_rule.this : key => rule.id }
}
