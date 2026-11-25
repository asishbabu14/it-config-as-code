resource "okta_app_signon_policy" "this" {
  name        = var.name
  description = var.description

  # The default rule denies. Only included_group_ids match the allow rule below.
  # This resource requires an Identity Engine org.
  catch_all = false
}

resource "okta_app_signon_policy_rule" "allow" {
  policy_id       = okta_app_signon_policy.this.id
  name            = var.rule_name
  status          = "ACTIVE"
  access          = "ALLOW"
  priority        = 1
  factor_mode     = "2FA"
  groups_included = var.included_group_ids

  constraints = [
    jsonencode({
      knowledge = {
        types = ["password"]
      }
    })
  ]
}
