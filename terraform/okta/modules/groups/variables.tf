variable "groups" {
  description = "Okta groups to create, keyed by a stable name used by other modules."
  type = map(object({
    name        = string
    description = string
  }))

  validation {
    condition = alltrue([
      for group in values(var.groups) : length(group.name) > 0 && length(group.name) <= 255
    ])
    error_message = "Each group name must be between 1 and 255 characters."
  }
}
