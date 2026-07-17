locals {
  public_gateway_hostname = "${var.browser_dns_record_name}.${var.browser_dns_zone_name}"
  private_core_hostname   = "core.${var.private_core_dns_zone_name}"
}

# The private CA signing key never leaves Key Vault. Platform Operations binds
# the configured private certificate issuer to this trust domain before apply;
# Terraform never generates, imports, or outputs private key bytes.
resource "azurerm_key_vault_key" "private_core_ca" {
  name         = "private-core-ca-signing"
  key_vault_id = azurerm_key_vault.app.id
  key_type     = "RSA"
  key_size     = 4096
  key_opts     = ["sign", "verify"]

  rotation_policy {
    automatic {
      time_before_expiry = "P90D"
    }
    expire_after         = "P730D"
    notify_before_expiry = "P120D"
  }

  tags       = merge(local.tags, { trust_domain = var.private_core_dns_zone_name })
  depends_on = [azurerm_role_assignment.platform_key_bootstrap]
}

resource "azurerm_key_vault_certificate" "public_gateway" {
  name         = "public-gateway-server"
  key_vault_id = azurerm_key_vault.app.id

  certificate_policy {
    issuer_parameters { name = var.public_certificate_issuer_name }
    key_properties {
      exportable = false
      key_size   = 3072
      key_type   = "RSA"
      reuse_key  = false
    }
    lifetime_action {
      action { action_type = "AutoRenew" }
      trigger { days_before_expiry = 30 }
    }
    secret_properties { content_type = "application/x-pkcs12" }
    x509_certificate_properties {
      subject            = "CN=${local.public_gateway_hostname}"
      validity_in_months = 3
      key_usage          = ["digitalSignature", "keyEncipherment"]
      extended_key_usage = ["1.3.6.1.5.5.7.3.1"]
      subject_alternative_names { dns_names = [local.public_gateway_hostname] }
    }
  }

  tags       = merge(local.tags, { lifecycle = "candidate-active-retired" })
  depends_on = [azurerm_role_assignment.platform_certificate_bootstrap]
}

resource "azurerm_key_vault_certificate" "private_core" {
  name         = "private-core-server"
  key_vault_id = azurerm_key_vault.app.id

  certificate_policy {
    issuer_parameters { name = var.private_core_certificate_issuer_name }
    key_properties {
      exportable = false
      key_size   = 3072
      key_type   = "RSA"
      reuse_key  = false
    }
    lifetime_action {
      action { action_type = "AutoRenew" }
      trigger { days_before_expiry = 30 }
    }
    secret_properties { content_type = "application/x-pkcs12" }
    x509_certificate_properties {
      subject            = "CN=${local.private_core_hostname}"
      validity_in_months = 3
      key_usage          = ["digitalSignature", "keyEncipherment"]
      extended_key_usage = ["1.3.6.1.5.5.7.3.1"]
      subject_alternative_names {
        dns_names = [
          local.private_core_hostname,
          "core.career-agent.svc",
          "core.career-agent.svc.cluster.local",
        ]
      }
    }
  }

  tags       = merge(local.tags, { trust_domain = var.private_core_dns_zone_name, lifecycle = "candidate-active-retired" })
  depends_on = [azurerm_role_assignment.platform_certificate_bootstrap, azurerm_key_vault_key.private_core_ca]
}

locals {
  gateway_certificate_versions = {
    public-gateway = {
      active_version      = azurerm_key_vault_certificate.public_gateway.version
      active_id           = azurerm_key_vault_certificate.public_gateway.id
      candidate_version   = null
      retired_versions    = []
      minimum_overlap     = "PT24H"
      retirement_deadline = "PT48H"
    }
    private-core = {
      active_version      = azurerm_key_vault_certificate.private_core.version
      active_id           = azurerm_key_vault_certificate.private_core.id
      candidate_version   = null
      retired_versions    = []
      minimum_overlap     = "PT24H"
      retirement_deadline = "PT48H"
      private_ca_key_id   = azurerm_key_vault_key.private_core_ca.resource_versionless_id
      issuer_name         = var.private_core_certificate_issuer_name
      trust_bundle = {
        source_certificate_id  = azurerm_key_vault_certificate.private_core.id
        distribution           = "key-vault-csi-public-x509-chain-only"
        private_key_exportable = false
      }
    }
  }

  gateway_certificate_rotation_contract = {
    state_machine = [
      "candidate-staged",
      "candidate-active",
      "partially-converged",
      "converged",
      "old-trust-retired",
      "rolled-back",
      "quarantined",
      "compromised-revoked",
    ]
    scheduled_interval  = "PT12H"
    candidate_overlap   = "PT24H"
    retirement_deadline = "PT48H"
    partial_retry       = "PT24H"
    probes = [
      "san",
      "issuer",
      "expiry",
      "trust",
      "reload",
      "tls",
      "route",
    ]
    evidence        = "versioned-nonsecret-per-transition"
    unsafe_fallback = false
    runner          = "scripts/azure/rotate-gateway-certificate.sh"
  }
}
