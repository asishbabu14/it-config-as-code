module "groups" {
  source = "../../modules/groups"

  groups = var.groups
}

module "conditional_access" {
  source = "../../modules/conditional_access"

  display_name = var.conditional_access.display_name
  included_group_ids = [
    for key in var.conditional_access.included_group_keys : module.groups.group_object_ids[key]
  ]
}

module "app_registration" {
  source = "../../modules/app_registration"

  display_name  = var.app.display_name
  homepage_url  = var.app.homepage_url
  redirect_uris = var.app.redirect_uris
}
