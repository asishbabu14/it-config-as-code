output "group_ids" {
  description = "Okta group ids keyed by the same keys as var.groups."
  value       = { for key, group in okta_group.this : key => group.id }
}
