resource "azuread_group" "this" {
  for_each = var.groups

  display_name            = each.value.display_name
  description             = each.value.description
  security_enabled        = true
  mail_enabled            = false
  prevent_duplicate_names = true
}
