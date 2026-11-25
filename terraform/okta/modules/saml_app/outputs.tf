output "app_id" {
  description = "Okta application id."
  value       = okta_app_saml.this.id
}

output "metadata_url" {
  description = "SAML metadata URL published by Okta for this application."
  value       = okta_app_saml.this.metadata_url
}

output "assignment_ids" {
  description = "App group assignment ids keyed by group key."
  value       = { for key, assignment in okta_app_group_assignment.this : key => assignment.id }
}
