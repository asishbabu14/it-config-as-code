variable "tenant_id" {
  description = "Entra tenant id. Set TF_VAR_tenant_id or pass -var. Do not commit a real tenant id if you do not want it public."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.tenant_id))
    error_message = "tenant_id must be a UUID."
  }
}

variable "client_id" {
  description = "Application id of the Terraform client."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.client_id))
    error_message = "client_id must be a UUID."
  }
}

variable "client_secret" {
  description = "Client secret for the Terraform client. Set TF_VAR_client_secret. Do not commit it."
  type        = string
  sensitive   = true
}

variable "groups" {
  description = "Security groups managed in the lab tenant."
  type = map(object({
    display_name = string
    description  = string
  }))
}

variable "conditional_access" {
  description = "Report-only conditional access policy. included_group_keys refer to keys in groups."
  type = object({
    display_name        = string
    included_group_keys = list(string)
  })
}

variable "app" {
  description = "Lab portal app registration."
  type = object({
    display_name  = string
    homepage_url  = string
    redirect_uris = list(string)
  })
}
