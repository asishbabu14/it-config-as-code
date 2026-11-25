resource "okta_group" "this" {
  for_each = var.groups

  name        = each.value.name
  description = each.value.description
}
