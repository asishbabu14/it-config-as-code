data "azuread_client_config" "current" {}

resource "azuread_application" "this" {
  display_name     = var.display_name
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azuread_client_config.current.object_id]

  web {
    homepage_url  = var.homepage_url
    redirect_uris = var.redirect_uris
  }

  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000"

    resource_access {
      # Delegated User.Read. Well-known scope id.
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d"
      type = "Scope"
    }
  }
}

resource "azuread_service_principal" "this" {
  client_id = azuread_application.this.client_id
  owners    = [data.azuread_client_config.current.object_id]
}
