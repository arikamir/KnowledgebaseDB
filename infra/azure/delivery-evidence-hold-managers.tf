# Hold managers can create, extend, and release request records and append/read
# their audit trail. They receive no assignment on delivery-evidence itself.
resource "azurerm_role_definition" "evidence_hold_manager_control" {
  name        = "${local.stem}-evidence-hold-manager-control"
  scope       = azurerm_resource_group.app.id
  description = "Create/read hold requests and append/read hold audit records without delete, evidence-content, legal-hold, or policy authority."
  permissions {
    actions = ["Microsoft.Storage/storageAccounts/blobServices/containers/read"]
    data_actions = [
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
    ]
    not_actions = [
      "Microsoft.Authorization/*",
      "Microsoft.Storage/storageAccounts/listKeys/action",
      "Microsoft.Storage/storageAccounts/blobServices/containers/write",
      "Microsoft.Storage/storageAccounts/blobServices/containers/delete",
      "Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/*",
      "Microsoft.Storage/storageAccounts/blobServices/containers/legalHolds/*",
    ]
    not_data_actions = [
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/write",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/move/action",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/permanentDelete/action",
    ]
  }
  assignable_scopes = [azurerm_resource_group.app.id]
}

resource "azurerm_role_assignment" "evidence_hold_manager_inventory" {
  scope              = azurerm_storage_container.evidence_hold_inventory.id
  role_definition_id = azurerm_role_definition.evidence_hold_manager_control.role_definition_resource_id
  principal_id       = var.evidence_hold_managers_group_object_id
  principal_type     = "Group"
}

resource "azurerm_role_assignment" "evidence_hold_manager_audit" {
  scope              = azurerm_storage_container.evidence_hold_audit.id
  role_definition_id = azurerm_role_definition.evidence_hold_manager_control.role_definition_resource_id
  principal_id       = var.evidence_hold_managers_group_object_id
  principal_type     = "Group"
}

# The reconciler reads control inventory but cannot create, update, or delete
# it. It has no hold-audit or delivery-blob content data action.
resource "azurerm_role_definition" "evidence_hold_inventory_reader" {
  name        = "${local.stem}-evidence-hold-inventory-reader"
  scope       = azurerm_resource_group.app.id
  description = "Read the isolated hold-control inventory only."
  permissions {
    actions          = ["Microsoft.Storage/storageAccounts/blobServices/containers/read"]
    data_actions     = ["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"]
    not_actions      = ["Microsoft.Authorization/*", "Microsoft.Storage/storageAccounts/listKeys/action"]
    not_data_actions = ["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action", "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write", "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete", "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/write"]
  }
  assignable_scopes = [azurerm_resource_group.app.id]
}

resource "azurerm_role_assignment" "evidence_hold_reconciler_inventory" {
  scope              = azurerm_storage_container.evidence_hold_inventory.id
  role_definition_id = azurerm_role_definition.evidence_hold_inventory_reader.role_definition_resource_id
  principal_id       = azurerm_user_assigned_identity.workload["evidence-hold-reconciler"].principal_id
}

# Set Blob Legal Hold authorizes through this one container/write action. The
# role is assigned only on delivery-evidence, has no DataActions, and explicitly
# excludes the control-plane policy/hold-tag surfaces. The reconciler script
# accepts only the complete enumerated blob-version inventory and sends an exact
# blob path plus versionid to the version-level data-plane operation.
resource "azurerm_role_definition" "evidence_version_hold_reconciler" {
  name        = "${local.stem}-evidence-version-hold-reconciler"
  scope       = azurerm_resource_group.app.id
  description = "Set or clear enumerated version-level blob legal holds without content, list, delete, writer, container-policy, or authorization access."
  permissions {
    actions = ["Microsoft.Storage/storageAccounts/blobServices/containers/write"]
    not_actions = [
      "Microsoft.Authorization/*",
      "Microsoft.Storage/storageAccounts/listKeys/action",
      "Microsoft.Storage/storageAccounts/blobServices/containers/read",
      "Microsoft.Storage/storageAccounts/blobServices/containers/delete",
      "Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/*",
      "Microsoft.Storage/storageAccounts/blobServices/containers/legalHolds/*",
    ]
    data_actions = []
    not_data_actions = [
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/write",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/move/action",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/permanentDelete/action",
    ]
  }
  assignable_scopes = [azurerm_resource_group.app.id]
}

resource "azurerm_role_assignment" "evidence_hold_reconciler_versions" {
  scope              = azurerm_storage_container.delivery_evidence.id
  role_definition_id = azurerm_role_definition.evidence_version_hold_reconciler.role_definition_resource_id
  principal_id       = azurerm_user_assigned_identity.workload["evidence-hold-reconciler"].principal_id
}

locals {
  evidence_hold_authorization_contract = {
    managers = {
      principal_id = var.evidence_hold_managers_group_object_id
      allowed      = ["hold-request-create-extend-release", "hold-audit-append-read"]
      denied       = ["delivery-blob-content", "direct-version-hold", "fixed-policy-mutation", "delete", "writer-role"]
    }
    reconciler = {
      principal_id = azurerm_user_assigned_identity.workload["evidence-hold-reconciler"].principal_id
      allowed      = ["hold-inventory-read", "enumerated-version-hold-set-clear"]
      denied       = ["delivery-blob-content-read-list-delete", "delivery-evidence-write", "hold-request-write", "hold-audit-access", "fixed-policy-mutation"]
    }
  }
}
