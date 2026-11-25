variable "rules" {
  description = "Group rules. group_key must match a key in group_ids."
  type = map(object({
    name       = string
    group_key  = string
    expression = string
    status     = string
  }))

  validation {
    condition = alltrue([
      for rule in values(var.rules) : contains(["ACTIVE", "INACTIVE"], rule.status)
    ])
    error_message = "Each group rule status must be ACTIVE or INACTIVE."
  }

  validation {
    condition = alltrue([
      for rule in values(var.rules) : length(rule.name) > 0 && length(rule.name) <= 50
    ])
    error_message = "Each group rule name must be between 1 and 50 characters."
  }
}

variable "group_ids" {
  description = "Map of group key to Okta group id."
  type        = map(string)
}
