resource "azurerm_key_vault_certificate" "bff_client" {
  name         = "bff-confidential-client"
  key_vault_id = azurerm_key_vault.app.id

  certificate_policy {
    issuer_parameters {
      name = "Self"
    }

    key_properties {
      exportable = true
      key_size   = 3072
      key_type   = "RSA"
      reuse_key  = false
    }

    lifetime_action {
      action {
        action_type = "AutoRenew"
      }
      trigger {
        days_before_expiry = 30
      }
    }

    secret_properties {
      content_type = "application/x-pem-file"
    }

    x509_certificate_properties {
      subject            = "CN=${var.prefix}-${var.environment}-learning-bff"
      validity_in_months = 3
      key_usage          = ["digitalSignature"]
      extended_key_usage = ["1.3.6.1.5.5.7.3.2"]
    }
  }

  tags = merge(local.tags, {
    purpose   = "entra-confidential-client"
    lifecycle = "candidate-active-retired"
  })

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [azurerm_role_assignment.platform_certificate_bootstrap]
}

output "bff_client_certificate" {
  description = "Non-secret Key Vault BFF client-certificate version and public metadata."
  value = {
    certificate_name           = azurerm_key_vault_certificate.bff_client.name
    certificate_version        = azurerm_key_vault_certificate.bff_client.version
    certificate_versionless_id = azurerm_key_vault_certificate.bff_client.versionless_id
    thumbprint                 = azurerm_key_vault_certificate.bff_client.thumbprint
    not_before                 = azurerm_key_vault_certificate.bff_client.certificate_attribute[0].not_before
    expires                    = azurerm_key_vault_certificate.bff_client.certificate_attribute[0].expires
    content_type               = "application/x-pem-file"
    private_key_location       = "key-vault-csi-only"
  }
}
