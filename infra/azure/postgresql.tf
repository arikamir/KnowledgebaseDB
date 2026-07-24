resource "azurerm_postgresql_flexible_server" "core" {
  name                          = "psql-${local.stem}"
  resource_group_name           = azurerm_resource_group.app.name
  location                      = azurerm_resource_group.app.location
  version                       = "16"
  delegated_subnet_id           = azurerm_subnet.postgresql.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgresql.id
  public_network_access_enabled = false
  zone                          = "1"
  sku_name                      = "GP_Standard_D2s_v3"
  storage_mb                    = 32768
  backup_retention_days         = 14
  geo_redundant_backup_enabled  = false

  identity {
    type = "SystemAssigned"
  }

  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = false
    tenant_id                     = var.tenant_id
  }

  tags       = local.tags
  depends_on = [azurerm_private_dns_zone_virtual_network_link.data_planes]
}

resource "azurerm_postgresql_flexible_server_active_directory_administrator" "platform_bootstrap" {
  server_name         = azurerm_postgresql_flexible_server.core.name
  resource_group_name = azurerm_resource_group.app.name
  tenant_id           = var.tenant_id
  object_id           = local.effective_postgresql_bootstrap_admin_object_id
  principal_name      = local.effective_postgresql_bootstrap_admin_name
  principal_type      = "Group"
}
