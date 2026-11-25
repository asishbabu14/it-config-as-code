resource "okta_app_saml" "this" {
  label                    = var.label
  status                   = var.status
  sso_url                  = var.sso_url
  recipient                = var.recipient
  destination              = var.destination
  audience                 = var.audience
  subject_name_id_template = "$${user.userName}"
  subject_name_id_format   = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
  response_signed          = true
  assertion_signed         = true
  signature_algorithm      = "RSA_SHA256"
  digest_algorithm         = "SHA256"
  honor_force_authn        = true
  authn_context_class_ref  = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"
  authentication_policy    = var.authentication_policy_id

  attribute_statements {
    name   = "email"
    values = ["user.email"]
  }

  attribute_statements {
    type         = "GROUP"
    name         = "groups"
    filter_type  = "REGEX"
    filter_value = "lab-.*"
  }
}

resource "okta_app_group_assignment" "this" {
  for_each = var.assigned_group_ids

  app_id   = okta_app_saml.this.id
  group_id = each.value
}
