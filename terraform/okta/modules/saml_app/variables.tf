variable "label" {
  description = "Display name of the SAML application."
  type        = string
}

variable "sso_url" {
  description = "SAML single sign-on URL on the relying party."
  type        = string
}

variable "recipient" {
  description = "SAML recipient URL. Usually the same as the single sign-on URL."
  type        = string
}

variable "destination" {
  description = "SAML destination URL. Usually the same as the single sign-on URL."
  type        = string
}

variable "audience" {
  description = "SAML audience restriction."
  type        = string
}

variable "authentication_policy_id" {
  description = "Id of the okta_app_signon_policy attached to this application."
  type        = string
}

variable "assigned_group_ids" {
  description = "Map of group key to Okta group id. Each group is assigned to the application."
  type        = map(string)
}

variable "status" {
  description = "Application status. ACTIVE or INACTIVE."
  type        = string
  default     = "ACTIVE"

  validation {
    condition     = contains(["ACTIVE", "INACTIVE"], var.status)
    error_message = "status must be ACTIVE or INACTIVE."
  }
}
