locals {
  core_application_roles = {
    "CareerAgent.Roadmap.Generate" = {
      id           = "599835a4-c40e-4cc4-88b6-9c11eab25723"
      display_name = "Generate application-owned roadmaps"
      description  = "Create roadmaps owned only by the validated machine application."
    }
    "CareerAgent.Guidance.Read" = {
      id           = "d74cbeb0-e7c8-43c9-b960-99709b9d48e8"
      display_name = "Read stateless skill guidance"
      description  = "Request supported stateless guidance as the validated machine application."
    }
    "CareerAgent.Progress.Write" = {
      id           = "17b3eaf8-4d32-452f-8ead-29eeaa7f4a42"
      display_name = "Write application-owned progress"
      description  = "Write progress only for roadmaps owned by the validated machine application."
    }
    "CareerAgent.Health.Read" = {
      id           = "ba6c64aa-f7d7-4894-82db-49ea48927417"
      display_name = "Read private health and compatibility"
      description  = "Read only nonpersonalized private health and compatibility resources."
    }
  }
}

resource "azuread_service_principal_delegated_permission_grant" "bff_core_employee" {
  service_principal_object_id          = azuread_service_principal.bff.object_id
  resource_service_principal_object_id = azuread_service_principal.core_api.object_id
  claim_values                         = [local.core_employee_scope]
}

resource "azuread_app_role_assignment" "bff_core_health" {
  app_role_id         = azuread_application.core_api.app_role_ids["CareerAgent.Health.Read"]
  principal_object_id = azuread_service_principal.bff.object_id
  resource_object_id  = azuread_service_principal.core_api.object_id
}

output "entra_core_application_roles" {
  description = "Non-secret exact core API application-role IDs and values."
  value = {
    for value, role in local.core_application_roles : value => {
      id                = azuread_application.core_api.app_role_ids[value]
      allowed_principal = "Application"
      description       = role.description
    }
  }
}
