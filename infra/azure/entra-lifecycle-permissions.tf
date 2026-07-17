data "azuread_application_published_app_ids" "well_known" {}

data "azuread_service_principal" "microsoft_graph" {
  client_id = data.azuread_application_published_app_ids.well_known.result.MicrosoftGraph
}

resource "azuread_app_role_assignment" "lifecycle_user_read_all" {
  app_role_id         = data.azuread_service_principal.microsoft_graph.app_role_ids["User.Read.All"]
  principal_object_id = azurerm_user_assigned_identity.workload["lifecycle"].principal_id
  resource_object_id  = data.azuread_service_principal.microsoft_graph.object_id
}

resource "azuread_app_role_assignment" "lifecycle_bff_session_revoke" {
  app_role_id         = azuread_application.bff.app_role_ids["LearningBff.Session.Revoke"]
  principal_object_id = azurerm_user_assigned_identity.workload["lifecycle"].principal_id
  resource_object_id  = azuread_service_principal.bff.object_id
}

output "entra_lifecycle_permissions" {
  description = "Non-secret administrator-consented lifecycle permission assignments."
  value = {
    principal_object_id            = azurerm_user_assigned_identity.workload["lifecycle"].principal_id
    graph_user_read_all_assignment = azuread_app_role_assignment.lifecycle_user_read_all.id
    bff_session_revoke_assignment  = azuread_app_role_assignment.lifecycle_bff_session_revoke.id
    granted_roles                  = ["User.Read.All", "LearningBff.Session.Revoke"]
  }
}
