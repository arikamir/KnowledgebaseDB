locals {
  bff_certificate_rotation_policy = {
    states = [
      "candidate-disabled",
      "candidate-active-overlap",
      "partially-converged",
      "converged",
      "prior-retired",
      "rolled-back",
      "quarantined",
      "emergency-revoked",
    ]
    normal = {
      candidate_available_before_retirement = "PT24H"
      retirement_deadline_after_activation  = "PT48H"
      previous_credential_remains_valid     = true
      force_reauthentication                = false
    }
    convergence = {
      every_current_replica = true
      probes = [
        "certificate-parse",
        "public-private-key-match",
        "thumbprint-version-match",
        "expiry",
        "fresh-sign-in-callback",
        "existing-session-refresh",
        "delegated-core-token",
        "health-app-token",
      ]
      nonconverged_replica_ready = false
    }
    partial = {
      retain_prior_credential   = true
      retry_window              = "PT24H"
      quarantine_candidate      = true
      explicit_operator_release = true
      page_routes               = ["application-operations", "platform-operations"]
      retire_prior              = false
    }
    rollback = {
      require_prior_version_safe  = true
      require_every_replica_probe = true
      failed_candidate_disabled   = true
    }
    emergency = {
      revoke_compromised_immediately = true
      overlap_requirement            = false
      unsafe_fallback_allowed        = false
      revoke_affected_sessions       = true
      clear_affected_token_caches    = true
      require_safe_reauthentication  = true
      preserve_saved_core_records    = true
    }
    evidence = {
      version_identifiers_only = true
      private_key_material     = false
      required_per_transition  = true
    }
    runtime_owner = "T076-T078"
    alert_owner   = "T189"
  }
}

output "bff_client_certificate_rotation_policy" {
  description = "Non-secret fail-closed BFF client-certificate lifecycle contract."
  value = merge(local.bff_certificate_rotation_policy, {
    active_key_vault_version = azurerm_key_vault_certificate.bff_client.version
    active_thumbprint        = azurerm_key_vault_certificate.bff_client.thumbprint
  })
}
