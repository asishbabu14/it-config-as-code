variable "okta_org_name" {
  description = "Okta org subdomain, the part before the base URL."
  type        = string

  validation {
    condition     = length(var.okta_org_name) > 0
    error_message = "okta_org_name must not be empty."
  }
}

variable "okta_base_url" {
  description = "Okta base URL, such as okta.com or oktapreview.com."
  type        = string
  default     = "okta.com"
}

variable "okta_api_token" {
  description = "Okta API token. Set TF_VAR_okta_api_token. Do not commit the token."
  type        = string
  sensitive   = true
}

variable "groups" {
  description = "Lab groups passed to the groups module."
  type = map(object({
    name        = string
    description = string
  }))
}

variable "group_rules" {
  description = "Lab group rules. group_key refers to a key in groups."
  type = map(object({
    name       = string
    group_key  = string
    expression = string
    status     = string
  }))
}

variable "signon_policy" {
  description = "Application sign-on policy and the group keys allowed to pass it."
  type = object({
    name                = string
    description         = string
    rule_name           = string
    included_group_keys = list(string)
  })
}

variable "saml_app" {
  description = "SAML application settings and the group keys assigned to it."
  type = object({
    label               = string
    sso_url             = string
    recipient           = string
    destination         = string
    audience            = string
    status              = string
    assigned_group_keys = list(string)
  })
}
