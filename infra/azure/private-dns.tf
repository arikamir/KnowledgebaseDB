resource "azurerm_private_dns_zone" "core" {
  name                = var.private_core_dns_zone_name
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "core" {
  name                  = "core-${local.stem}"
  resource_group_name   = azurerm_resource_group.app.name
  private_dns_zone_name = azurerm_private_dns_zone.core.name
  virtual_network_id    = azurerm_virtual_network.app.id
  registration_enabled  = false
  tags                  = local.tags
}

resource "azurerm_private_dns_a_record" "core" {
  name                = "core"
  zone_name           = azurerm_private_dns_zone.core.name
  resource_group_name = azurerm_resource_group.app.name
  ttl                 = 300
  records             = [var.private_core_load_balancer_ip]
  tags                = local.tags
}
