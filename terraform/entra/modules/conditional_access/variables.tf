variable "display_name" {
  description = "Display name of the conditional access policy."
  type        = string
}

variable "included_group_ids" {
  description = "Group object ids the policy evaluates. The policy stays in report-only mode."
  type        = list(string)

  validation {
    condition     = length(var.included_group_ids) > 0
    error_message = "Include at least one group."
  }
}
