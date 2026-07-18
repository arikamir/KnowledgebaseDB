locals {
  delivery_evidence_storage_name = "st${substr(var.prefix, 0, 8)}${substr(sha256("${var.subscription_id}:${var.environment}:delivery-evidence"), 0, 12)}"
  evidence_hold_storage_name     = "st${substr(var.prefix, 0, 8)}${substr(sha256("${var.subscription_id}:${var.environment}:evidence-holds"), 0, 12)}"
  publisher_evidence_stages      = ["validation", "build", "scan", "publish", "pre-promotion"]
  deployer_evidence_stages       = ["promotion", "migration", "core", "bff", "ui", "verify", "rollback", "final"]

  evidence_blob_path_attribute = "@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path]"
  publisher_evidence_condition = "((@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringEquals 'delivery-evidence') AND (${join(" OR ", [for stage in local.publisher_evidence_stages : "(${local.evidence_blob_path_attribute} StringLike 'deliveries/${var.environment}/*/${stage}/*')"])}))"
  deployer_evidence_condition  = "((@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringEquals 'delivery-evidence') AND (${join(" OR ", [for stage in local.deployer_evidence_stages : "(${local.evidence_blob_path_attribute} StringLike 'deliveries/${var.environment}/*/${stage}/*')"])}))"
}

# This account enables account-level version WORM at creation. Each accepted
# evidence blob version inherits the fixed 90-day policy; the application
# records its immutable_until as created_at + 90 days and cannot mutate it.
resource "azurerm_storage_account" "delivery_evidence" {
  name                            = local.delivery_evidence_storage_name
  resource_group_name             = azurerm_resource_group.app.name
  location                        = azurerm_resource_group.app.location
  account_tier                    = "Standard"
  account_replication_type        = "ZRS"
  account_kind                    = "StorageV2"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  public_network_access_enabled   = false

  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = true
  }

  immutability_policy {
    allow_protected_append_writes = false
    period_since_creation_in_days = 90
    # Azure permits a new account-level policy to start only as Disabled or
    # Unlocked. Formal delivery locks it in a reviewed second apply; the PoC
    # remains Unlocked because it cannot publish protected-release evidence.
    state = var.delivery_evidence_policy_state
  }

  tags = local.tags
}

resource "azurerm_storage_container" "delivery_evidence" {
  name                  = "delivery-evidence"
  storage_account_id    = azurerm_storage_account.delivery_evidence.id
  container_access_type = "private"
}

resource "azurerm_role_definition" "delivery_evidence_exact_writer" {
  name        = "${local.stem}-delivery-evidence-exact-writer"
  scope       = azurerm_resource_group.app.id
  description = "Create immutable evidence and verify an exact path/version; no list, tag, legal-hold, delete, overwrite, policy, or authorization authority."
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
      "Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/*",
      "Microsoft.Storage/storageAccounts/blobServices/containers/setLegalHold/action",
      "Microsoft.Storage/storageAccounts/blobServices/containers/clearLegalHold/action",
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

resource "azurerm_role_assignment" "publisher_evidence_prefix" {
  scope              = azurerm_storage_container.delivery_evidence.id
  role_definition_id = azurerm_role_definition.delivery_evidence_exact_writer.role_definition_resource_id
  principal_id       = azurerm_user_assigned_identity.jenkins_publisher.principal_id
  condition_version  = "2.0"
  condition          = local.publisher_evidence_condition
}

resource "azurerm_role_assignment" "deployer_evidence_prefix" {
  scope              = azurerm_storage_container.delivery_evidence.id
  role_definition_id = azurerm_role_definition.delivery_evidence_exact_writer.role_definition_resource_id
  principal_id       = azurerm_user_assigned_identity.jenkins_deployer.principal_id
  condition_version  = "2.0"
  condition          = local.deployer_evidence_condition
}

resource "azurerm_role_assignment" "delivery_evidence_reader" {
  for_each = {
    delivery-operators = local.effective_delivery_operators_group_object_id
    security-reviewers = local.effective_security_reviewers_group_object_id
  }
  scope                = azurerm_storage_container.delivery_evidence.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = each.value
  principal_type       = "Group"
}

# Lifecycle deletion is only an eligibility request. Azure skips deletion
# while a version-level legal hold remains or its fixed immutable_until has not
# elapsed, so release never shortens the base lock.
resource "azurerm_storage_management_policy" "delivery_evidence" {
  storage_account_id = azurerm_storage_account.delivery_evidence.id

  rule {
    name    = "delete-unheld-evidence-after-base-lock"
    enabled = true

    filters {
      prefix_match = ["deliveries/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        delete_after_days_since_creation_greater_than = 90
      }
      version {
        delete_after_days_since_creation = 90
      }
    }
  }
}

# Hold request inventory and append-only audit are deliberately isolated from
# evidence content. This account has no evidence WORM policy to mutate: the
# reconciler can update control state without any route to the fixed 90-day
# policy on azurerm_storage_account.delivery_evidence.
resource "azurerm_storage_account" "evidence_hold_control" {
  name                            = local.evidence_hold_storage_name
  resource_group_name             = azurerm_resource_group.app.name
  location                        = azurerm_resource_group.app.location
  account_tier                    = "Standard"
  account_replication_type        = "ZRS"
  account_kind                    = "StorageV2"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  public_network_access_enabled   = false

  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = true
  }

  tags = local.tags
}

resource "azurerm_storage_container" "evidence_hold_inventory" {
  name                  = "hold-inventory"
  storage_account_id    = azurerm_storage_account.evidence_hold_control.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "evidence_hold_audit" {
  name                  = "hold-audit"
  storage_account_id    = azurerm_storage_account.evidence_hold_control.id
  container_access_type = "private"
}

resource "azurerm_storage_container_immutability_policy" "evidence_hold_audit" {
  storage_container_resource_manager_id = azurerm_storage_container.evidence_hold_audit.id
  immutability_period_in_days           = 180
  locked                                = true
  protected_append_writes_enabled       = true
}

# Control records carry created_at/expires_at and are rejected by T187 when
# expires_at exceeds created_at + 180 days. This lifecycle is only bounded
# cleanup for those records and never references the delivery-evidence account.
resource "azurerm_storage_management_policy" "evidence_hold_control" {
  storage_account_id = azurerm_storage_account.evidence_hold_control.id

  rule {
    name    = "expire-hold-control-records"
    enabled = true

    filters {
      prefix_match = ["hold-inventory/", "hold-audit/"]
      blob_types   = ["blockBlob", "appendBlob"]
    }

    actions {
      base_blob {
        delete_after_days_since_creation_greater_than = 180
      }
      version {
        delete_after_days_since_creation = 180
      }
    }
  }
}

output "delivery_evidence_storage_account_id" {
  value = azurerm_storage_account.delivery_evidence.id
}

output "delivery_evidence_container_id" {
  value = azurerm_storage_container.delivery_evidence.id
}

output "delivery_evidence_reader_assignment_ids" {
  value = { for name, assignment in azurerm_role_assignment.delivery_evidence_reader : name => assignment.id }
}

output "evidence_hold_control_storage_account_id" {
  value = azurerm_storage_account.evidence_hold_control.id
}

output "evidence_hold_inventory_container_id" {
  value = azurerm_storage_container.evidence_hold_inventory.id
}

output "evidence_hold_audit_container_id" {
  value = azurerm_storage_container.evidence_hold_audit.id
}
