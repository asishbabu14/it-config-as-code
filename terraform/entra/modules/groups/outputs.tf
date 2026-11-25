output "group_object_ids" {
  description = "Group object ids keyed by the same keys as var.groups."
  value       = { for key, group in azuread_group.this : key => group.object_id }
}
