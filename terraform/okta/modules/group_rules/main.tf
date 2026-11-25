resource "okta_group_rule" "this" {
  for_each = var.rules

  name              = each.value.name
  status            = each.value.status
  expression_value  = each.value.expression
  group_assignments = [var.group_ids[each.value.group_key]]
}
