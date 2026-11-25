variable "name" {
  description = "Name of the application sign-on policy."
  type        = string
}

variable "description" {
  description = "Description of the application sign-on policy."
  type        = string
}

variable "rule_name" {
  description = "Name of the allow rule inside the sign-on policy."
  type        = string
}

variable "included_group_ids" {
  description = "Okta group ids that match the allow rule. Everyone else hits the deny catch-all."
  type        = list(string)

  validation {
    condition     = length(var.included_group_ids) > 0
    error_message = "Include at least one group. The catch-all rule denies everyone else."
  }
}
