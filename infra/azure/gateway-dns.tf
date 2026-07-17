resource "azurerm_dns_zone" "browser" {
  name                = var.browser_dns_zone_name
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.tags
}

resource "azurerm_dns_cname_record" "browser" {
  name                = var.browser_dns_record_name
  zone_name           = azurerm_dns_zone.browser.name
  resource_group_name = azurerm_resource_group.app.name
  ttl                 = 300
  record              = azurerm_application_load_balancer_frontend.public.fully_qualified_domain_name
  tags                = local.tags
}

resource "azurerm_dns_txt_record" "browser_certificate_validation" {
  name                = "_acme-challenge.${var.browser_dns_record_name}"
  zone_name           = azurerm_dns_zone.browser.name
  resource_group_name = azurerm_resource_group.app.name
  ttl                 = 60
  record { value = "platform-operations-managed-validation" }
  tags = local.tags
}
