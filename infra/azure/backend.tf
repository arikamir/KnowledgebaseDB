terraform {
  # Platform Operations supplies the storage account, container, key, tenant,
  # and subscription with -backend-config. Azure Blob leases provide locking.
  backend "azurerm" {
    use_azuread_auth = true
    use_oidc         = false
  }
}
