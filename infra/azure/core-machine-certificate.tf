resource "azurerm_role_definition" "gateway_certificate_versions" {
  name        = "${local.stem}-gateway-certificate-versions"
  scope       = azurerm_resource_group.app.id
  description = "Create/import/read metadata and enable/disable versions of only the assigned certificates; no private-key secret export or deletion."
  permissions {
    actions = ["Microsoft.KeyVault/vaults/read"]
    data_actions = [
      "Microsoft.KeyVault/vaults/certificates/read",
      "Microsoft.KeyVault/vaults/certificates/create/action",
      "Microsoft.KeyVault/vaults/certificates/import/action",
      "Microsoft.KeyVault/vaults/certificates/update/action",
    ]
    not_actions = [
      "Microsoft.Authorization/*",
      "Microsoft.KeyVault/vaults/secrets/read",
    ]
    not_data_actions = [
      "Microsoft.KeyVault/vaults/secrets/readMetadata/action",
      "Microsoft.KeyVault/vaults/secrets/getSecret/action",
      "Microsoft.KeyVault/vaults/certificates/delete",
      "Microsoft.KeyVault/vaults/certificates/purge/action",
      "Microsoft.KeyVault/vaults/keys/*",
    ]
  }
  assignable_scopes = [azurerm_resource_group.app.id]
}

resource "azurerm_role_assignment" "gateway_certificate_versions" {
  for_each = merge(var.technical_poc_mode ? {} : {
    public-gateway = "${azurerm_key_vault.app.id}/certificates/${azurerm_key_vault_certificate.public_gateway[0].name}"
    }, {
    private-core = "${azurerm_key_vault.app.id}/certificates/${azurerm_key_vault_certificate.private_core.name}"
  })
  scope              = each.value
  role_definition_id = azurerm_role_definition.gateway_certificate_versions.role_definition_resource_id
  principal_id       = azurerm_user_assigned_identity.workload["gateway-certificate-dns"].principal_id
}

resource "azurerm_role_definition" "gateway_named_dns_records" {
  name        = "${local.stem}-gateway-named-dns-records"
  scope       = azurerm_resource_group.app.id
  description = "Read/write only the assigned browser CNAME/TXT and private-core A records without zone deletion or unrelated record access."
  permissions {
    actions = [
      "Microsoft.Network/dnsZones/CNAME/read",
      "Microsoft.Network/dnsZones/CNAME/write",
      "Microsoft.Network/dnsZones/TXT/read",
      "Microsoft.Network/dnsZones/TXT/write",
      "Microsoft.Network/privateDnsZones/A/read",
      "Microsoft.Network/privateDnsZones/A/write",
    ]
    not_actions = [
      "Microsoft.Authorization/*",
      "Microsoft.Network/dnsZones/delete",
      "Microsoft.Network/privateDnsZones/delete",
      "Microsoft.Network/dnsZones/*/delete",
      "Microsoft.Network/privateDnsZones/*/delete",
    ]
    data_actions     = []
    not_data_actions = []
  }
  assignable_scopes = [azurerm_resource_group.app.id]
}

resource "azurerm_role_assignment" "gateway_named_dns_records" {
  for_each = merge(var.technical_poc_mode ? {} : {
    browser-cname = azurerm_dns_cname_record.browser[0].id
    browser-txt   = azurerm_dns_txt_record.browser_certificate_validation[0].id
    }, {
    private-core-a = azurerm_private_dns_a_record.core.id
  })
  scope              = each.value
  role_definition_id = azurerm_role_definition.gateway_named_dns_records.role_definition_resource_id
  principal_id       = azurerm_user_assigned_identity.workload["gateway-certificate-dns"].principal_id
}

resource "azurerm_role_assignment" "core_tls_certificate_csi" {
  scope                = "${azurerm_key_vault.app.id}/secrets/${azurerm_key_vault_certificate.private_core.name}"
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.workload["core"].principal_id
}

resource "azurerm_role_assignment" "core_tls_public_certificate_csi" {
  scope                = "${azurerm_key_vault.app.id}/certificates/${azurerm_key_vault_certificate.private_core.name}"
  role_definition_name = "Key Vault Certificate User"
  principal_id         = azurerm_user_assigned_identity.workload["core"].principal_id
}
