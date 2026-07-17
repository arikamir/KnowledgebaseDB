locals {
  bff_browser_origin = "https://${local.public_gateway_hostname}"
  bff_redirect_uri   = "${local.bff_browser_origin}/bff/v1/auth/callback"
  bff_logout_uri     = "${local.bff_browser_origin}/bff/v1/auth/logout"
  bff_api_audience   = "api://${var.tenant_id}/${var.prefix}-${var.environment}-learning-bff"
}

resource "azuread_application" "bff" {
  display_name     = "${var.prefix}-${var.environment}-learning-bff"
  description      = "Single-tenant confidential BFF web client and lifecycle-revocation API."
  identifier_uris  = [local.bff_api_audience]
  owners           = [data.azuread_client_config.current.object_id]
  sign_in_audience = "AzureADMyOrg"

  fallback_public_client_enabled = false
  prevent_duplicate_names        = true

  api {
    requested_access_token_version = 2
  }

  app_role {
    allowed_member_types = ["Application"]
    description          = "Revoke all BFF sessions for one lifecycle-confirmed departed employee."
    display_name         = "Revoke learning BFF sessions"
    enabled              = true
    id                   = "d7bb2bf9-99f4-4c7c-a51b-318b96d48ad6"
    value                = "LearningBff.Session.Revoke"
  }

  required_resource_access {
    resource_app_id = azuread_application.core_api.client_id

    resource_access {
      id   = azuread_application.core_api.oauth2_permission_scope_ids[local.core_employee_scope]
      type = "Scope"
    }

    resource_access {
      id   = azuread_application.core_api.app_role_ids["CareerAgent.Health.Read"]
      type = "Role"
    }
  }

  web {
    homepage_url  = local.bff_browser_origin
    redirect_uris = [local.bff_redirect_uri]
    logout_url    = local.bff_logout_uri

    implicit_grant {
      access_token_issuance_enabled = false
      id_token_issuance_enabled     = false
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_service_principal" "bff" {
  client_id                    = azuread_application.bff.client_id
  app_role_assignment_required = true
  owners                       = [data.azuread_client_config.current.object_id]

  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_application_certificate" "bff_active" {
  application_id = azuread_application.bff.id
  type           = "AsymmetricX509Cert"
  encoding       = "hex"
  value          = azurerm_key_vault_certificate.bff_client.certificate_data
  start_date     = azurerm_key_vault_certificate.bff_client.certificate_attribute[0].not_before
  end_date       = azurerm_key_vault_certificate.bff_client.certificate_attribute[0].expires

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [value, start_date, end_date]
  }
}

output "entra_bff_registration" {
  description = "Non-secret BFF confidential-client and protected internal-API registration metadata."
  value = {
    application_object_id       = azuread_application.bff.object_id
    client_id                   = azuread_application.bff.client_id
    service_principal_object_id = azuread_service_principal.bff.object_id
    sign_in_audience            = azuread_application.bff.sign_in_audience
    redirect_uri                = local.bff_redirect_uri
    logout_uri                  = local.bff_logout_uri
    internal_api_audience       = local.bff_api_audience
    session_revoke_role_id      = azuread_application.bff.app_role_ids["LearningBff.Session.Revoke"]
    session_revoke_role_value   = "LearningBff.Session.Revoke"
    certificate_registration_id = azuread_application_certificate.bff_active.id
    certificate_thumbprint      = azurerm_key_vault_certificate.bff_client.thumbprint
    certificate_version         = azurerm_key_vault_certificate.bff_client.version
    certificate_material        = "public-x509-only"
    certificate_rotation_owner  = "T076-T078"
    import_application_command  = "terraform -chdir=infra/azure import azuread_application.bff /applications/<application-object-id>"
    import_principal_command    = "terraform -chdir=infra/azure import azuread_service_principal.bff /servicePrincipals/<service-principal-object-id>"
  }
}
