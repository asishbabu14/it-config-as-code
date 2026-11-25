variable "display_name" {
  description = "Display name of the app registration."
  type        = string
}

variable "homepage_url" {
  description = "Homepage URL shown on the app registration."
  type        = string
}

variable "redirect_uris" {
  description = "Web redirect URIs for the lab portal."
  type        = list(string)

  validation {
    condition     = length(var.redirect_uris) > 0
    error_message = "Provide at least one redirect URI."
  }
}
