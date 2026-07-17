resource "azurerm_key_vault" "app" {
  name                          = substr("kv${replace(local.stem, "-", "")}", 0, 24)
  location                      = azurerm_resource_group.app.location
  resource_group_name           = azurerm_resource_group.app.name
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  purge_protection_enabled      = true
  soft_delete_retention_days    = 90
  public_network_access_enabled = false
  tags                          = local.tags
}

resource "azurerm_private_endpoint" "key_vault" {
  name                = "pe-key-vault-${local.stem}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.tags

  private_service_connection {
    name                           = "key-vault"
    private_connection_resource_id = azurerm_key_vault.app.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "key-vault"
    private_dns_zone_ids = [azurerm_private_dns_zone.key_vault.id]
  }
}

# The interactive Platform Operations principal can create and rotate keys but
# receives no secret-reading role. PIM expiry governs the principal itself.
resource "azurerm_role_assignment" "platform_key_bootstrap" {
  scope                = azurerm_key_vault.app.id
  role_definition_name = "Key Vault Crypto Officer"
  principal_id         = data.azuread_client_config.current.object_id
}

resource "azurerm_role_assignment" "platform_certificate_bootstrap" {
  scope                = azurerm_key_vault.app.id
  role_definition_name = "Key Vault Certificates Officer"
  principal_id         = data.azuread_client_config.current.object_id
}
