locals {
  core_api_audience       = "api://${var.tenant_id}/${var.prefix}-${var.environment}-career-agent-core"
  core_employee_scope     = "CareerAgent.Access"
  core_employee_scope_uri = "${local.core_api_audience}/${local.core_employee_scope}"
}

resource "azuread_application" "core_api" {
  display_name     = "${var.prefix}-${var.environment}-career-agent-core"
  description      = "Single-tenant protected API for delegated employees and approved machine consumers."
  identifier_uris  = [local.core_api_audience]
  owners           = [data.azuread_client_config.current.object_id]
  sign_in_audience = "AzureADMyOrg"

  fallback_public_client_enabled = false
  prevent_duplicate_names        = true

  api {
    requested_access_token_version = 2

    oauth2_permission_scope {
      admin_consent_description  = "Allow the learning BFF to access Career Agent as the signed-in employee."
      admin_consent_display_name = "Access Career Agent as an employee"
      enabled                    = true
      id                         = "2813194f-3c08-46f3-8c14-9cb6206af2ab"
      type                       = "User"
      user_consent_description   = "Allow the learning experience to access Career Agent on your behalf."
      user_consent_display_name  = "Access Career Agent"
      value                      = local.core_employee_scope
    }
  }

  dynamic "app_role" {
    for_each = local.core_application_roles
    content {
      allowed_member_types = ["Application"]
      description          = app_role.value.description
      display_name         = app_role.value.display_name
      enabled              = true
      id                   = app_role.value.id
      value                = app_role.key
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_service_principal" "core_api" {
  client_id                    = azuread_application.core_api.client_id
  app_role_assignment_required = true
  owners                       = [data.azuread_client_config.current.object_id]

  lifecycle {
    prevent_destroy = true
  }
}

output "entra_core_api_registration" {
  description = "Non-secret protected core API registration, audience, and delegated-scope metadata."
  value = {
    application_object_id       = azuread_application.core_api.object_id
    client_id                   = azuread_application.core_api.client_id
    service_principal_object_id = azuread_service_principal.core_api.object_id
    audience                    = local.core_api_audience
    employee_scope_value        = local.core_employee_scope
    employee_scope_id           = azuread_application.core_api.oauth2_permission_scope_ids[local.core_employee_scope]
    employee_scope_uri          = local.core_employee_scope_uri
    access_token_version        = 2
    import_application_command  = "terraform -chdir=infra/azure import azuread_application.core_api /applications/<application-object-id>"
    import_principal_command    = "terraform -chdir=infra/azure import azuread_service_principal.core_api /servicePrincipals/<service-principal-object-id>"
  }
}
