resource "azuread_conditional_access_policy" "this" {
  display_name = var.display_name

  # Hardcoded on purpose. Turning enforcement on is a module edit, so the
  # review shows the state line instead of a tfvars flip.
  state = "enabledForReportingButNotEnforced"

  conditions {
    client_app_types = ["all"]

    applications {
      included_applications = ["All"]
      excluded_applications = []
    }

    users {
      included_groups = var.included_group_ids
      excluded_groups = []
      included_users  = []
      excluded_users  = []
    }
  }

  grant_controls {
    operator          = "OR"
    built_in_controls = ["mfa"]
  }
}
