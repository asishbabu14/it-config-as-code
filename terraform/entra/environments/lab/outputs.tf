output "group_object_ids" {
  description = "Object ids of the lab security groups."
  value       = module.groups.group_object_ids
}

output "conditional_access_policy_id" {
  description = "Object id of the report-only conditional access policy."
  value       = module.conditional_access.policy_id
}

output "app_client_id" {
  description = "Application id of the lab portal."
  value       = module.app_registration.client_id
}

output "service_principal_object_id" {
  description = "Object id of the lab portal service principal."
  value       = module.app_registration.service_principal_object_id
}
