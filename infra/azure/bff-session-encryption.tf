resource "azurerm_key_vault_key" "bff_session" {
  name         = "bff-session-encryption"
  key_vault_id = azurerm_key_vault.app.id
  key_type     = "RSA"
  key_size     = 3072
  key_opts     = ["decrypt", "encrypt", "unwrapKey", "wrapKey"]

  rotation_policy {
    automatic {
      time_before_expiry = "P30D"
    }
    expire_after         = "P180D"
    notify_before_expiry = "P45D"
  }

  tags       = merge(local.tags, { key_ring = "active" })
  depends_on = [azurerm_role_assignment.platform_key_bootstrap]
}

resource "azurerm_role_assignment" "bff_session_crypto" {
  scope                = azurerm_key_vault_key.bff_session.resource_versionless_id
  role_definition_name = "Key Vault Crypto User"
  principal_id         = azurerm_user_assigned_identity.workload["bff"].principal_id
}

locals {
  bff_session_key_ring = {
    active_version = azurerm_key_vault_key.bff_session.version
    active_key_id  = azurerm_key_vault_key.bff_session.id
    # Operators add prior uncompromised versions during overlap; no private key
    # bytes or wrapping material are represented in Terraform.
    decrypt_only_versions = []
    compromised_response  = "revoke-indexed-sessions-before-disable"
  }
}

output "bff_session_key_ring" {
  description = "Non-secret active/decrypt-only key-version configuration."
  value       = local.bff_session_key_ring
}
