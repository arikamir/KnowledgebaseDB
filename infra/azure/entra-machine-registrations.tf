locals {
  machine_role_assignments = merge([
    for machine_key, machine in var.approved_machine_consumers : {
      for role in machine.roles : "${machine_key}|${role}" => {
        machine_key = machine_key
        role        = role
      }
    }
  ]...)
}

resource "azuread_application" "machine" {
  for_each = var.approved_machine_consumers

  display_name     = each.value.display_name
  description      = "Approved private Career Agent machine client '${each.key}'."
  owners           = [data.azuread_client_config.current.object_id]
  sign_in_audience = "AzureADMyOrg"

  fallback_public_client_enabled = false
  prevent_duplicate_names        = true

  required_resource_access {
    resource_app_id = azuread_application.core_api.client_id

    dynamic "resource_access" {
      for_each = each.value.roles
      content {
        id   = azuread_application.core_api.app_role_ids[resource_access.value]
        type = "Role"
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_service_principal" "machine" {
  for_each = var.approved_machine_consumers

  client_id                    = azuread_application.machine[each.key].client_id
  app_role_assignment_required = true
  owners                       = [data.azuread_client_config.current.object_id]

  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_app_role_assignment" "machine_core" {
  for_each = local.machine_role_assignments

  app_role_id         = azuread_application.core_api.app_role_ids[each.value.role]
  principal_object_id = azuread_service_principal.machine[each.value.machine_key].object_id
  resource_object_id  = azuread_service_principal.core_api.object_id
}

output "entra_machine_registrations" {
  description = "Non-secret approved machine client IDs, principal IDs, and exact assigned roles."
  value = {
    for key, machine in var.approved_machine_consumers : key => {
      application_object_id       = azuread_application.machine[key].object_id
      client_id                   = azuread_application.machine[key].client_id
      service_principal_object_id = azuread_service_principal.machine[key].object_id
      roles                       = sort(tolist(machine.roles))
    }
  }
}
