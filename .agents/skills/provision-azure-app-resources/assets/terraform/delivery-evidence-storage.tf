locals { delivery_evidence_storage_name = "st${substr(var.prefix, 0, 8)}${substr(sha256("${var.subscription_id}:${var.environment}:delivery-evidence"), 0, 12)}" }
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
