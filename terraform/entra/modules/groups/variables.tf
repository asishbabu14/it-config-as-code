variable "groups" {
  description = "Security groups to create, keyed by a stable name."
  type = map(object({
    display_name = string
    description  = string
  }))

  validation {
    condition = alltrue([
      for group in values(var.groups) : length(group.display_name) > 0
    ])
    error_message = "Each group needs a display name."
  }
}
