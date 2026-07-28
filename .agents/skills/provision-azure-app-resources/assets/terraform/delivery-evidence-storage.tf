locals {
  delivery_evidence_storage_name = "st${substr(var.prefix, 0, 8)}${substr(sha256("${var.subscription_id}:${var.environment}:delivery-evidence"), 0, 12)}"
  publisher_evidence_stages      = ["validation", "build", "scan", "publish", "pre-promotion"]
  deployer_evidence_stages       = ["promotion", "migration", "core", "bff", "ui", "verify", "rollback", "final"]
  evidence_blob_path_attribute   = "@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path]"
  publisher_evidence_condition   = "((@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringEquals 'delivery-evidence') AND (${join(" OR ", [for stage in local.publisher_evidence_stages : "(${local.evidence_blob_path_attribute} StringLike 'deliveries/${var.environment}/*/${stage}/*')"])}))"
  deployer_evidence_condition    = "((@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringEquals 'delivery-evidence') AND (${join(" OR ", [for stage in local.deployer_evidence_stages : "(${local.evidence_blob_path_attribute} StringLike 'deliveries/${var.environment}/*/${stage}/*')"])}))"
}
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
    state                         = "Locked"
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
  description = "Create and exactly verify immutable evidence without list, tag, legal-hold, delete, overwrite, policy, or authorization authority."
  permissions {
    actions      = ["Microsoft.Storage/storageAccounts/blobServices/containers/read"]
    data_actions = ["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action", "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write", "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"]
    not_actions  = ["Microsoft.Authorization/*", "Microsoft.Storage/storageAccounts/listKeys/action", "Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/*", "Microsoft.Storage/storageAccounts/blobServices/containers/legalHolds/*"]
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
  principal_id       = azurerm_user_assigned_identity.github_actions_publisher.principal_id
  condition_version  = "2.0"
  condition          = local.publisher_evidence_condition
}
resource "azurerm_role_assignment" "delivery_evidence_reader" {
  for_each = {
    delivery-operators = var.delivery_operators_group_object_id
    security-reviewers = var.security_reviewers_group_object_id
  }
  scope                = azurerm_storage_container.delivery_evidence.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = each.value
  principal_type       = "Group"
}
