resource "azurerm_managed_redis" "bff" {
  name                      = "redis-${local.stem}"
  location                  = azurerm_resource_group.app.location
  resource_group_name       = azurerm_resource_group.app.name
  sku_name                  = var.managed_redis_sku
  public_network_access     = "Disabled"
  high_availability_enabled = true
  tags                      = local.tags

  default_database {
    access_keys_authentication_enabled = false
    client_protocol                    = "Encrypted"
    clustering_policy                  = "EnterpriseCluster"
    eviction_policy                    = "VolatileLRU"
  }
}

resource "azurerm_private_endpoint" "redis" {
  name                = "pe-redis-${local.stem}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.tags

  private_service_connection {
    name                           = "managed-redis"
    private_connection_resource_id = azurerm_managed_redis.bff.id
    subresource_names              = ["redisEnterprise"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "managed-redis"
    private_dns_zone_ids = [azurerm_private_dns_zone.redis.id]
  }
}

resource "azurerm_managed_redis_access_policy_assignment" "bff" {
  managed_redis_id = azurerm_managed_redis.bff.id
  object_id        = azurerm_user_assigned_identity.workload["bff"].principal_id
}
