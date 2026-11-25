output "client_id" {
  description = "Application (client) id of the lab portal."
  value       = azuread_application.this.client_id
}

output "object_id" {
  description = "Object id of the app registration."
  value       = azuread_application.this.object_id
}

output "service_principal_object_id" {
  description = "Object id of the service principal created for the app."
  value       = azuread_service_principal.this.object_id
}
