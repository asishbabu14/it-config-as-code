module "groups" {
  source = "../../modules/groups"

  groups = var.groups
}

module "group_rules" {
  source = "../../modules/group_rules"

  rules     = var.group_rules
  group_ids = module.groups.group_ids
}

module "signon_policy" {
  source = "../../modules/signon_policy"

  name        = var.signon_policy.name
  description = var.signon_policy.description
  rule_name   = var.signon_policy.rule_name
  included_group_ids = [
    for key in var.signon_policy.included_group_keys : module.groups.group_ids[key]
  ]
}

module "saml_app" {
  source = "../../modules/saml_app"

  label                    = var.saml_app.label
  sso_url                  = var.saml_app.sso_url
  recipient                = var.saml_app.recipient
  destination              = var.saml_app.destination
  audience                 = var.saml_app.audience
  status                   = var.saml_app.status
  authentication_policy_id = module.signon_policy.policy_id
  assigned_group_ids = {
    for key in var.saml_app.assigned_group_keys : key => module.groups.group_ids[key]
  }
}
