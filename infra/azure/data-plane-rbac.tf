locals {
  # Azure creates/federates these principals. The reviewed external SQL maps
  # their immutable object IDs to object-level PostgreSQL roles and proves every
  # denied edge before password fallback remains disabled.
  postgresql_data_plane_contract = {
    core-dml = {
      object_id = azurerm_user_assigned_identity.workload["core"].principal_id
      allowed   = ["application-schema-select-insert-update-delete"]
      denied    = ["ddl", "retention-procedures", "lifecycle-tables", "lab-validation-state"]
    }
    lifecycle = {
      object_id = azurerm_user_assigned_identity.workload["lifecycle"].principal_id
      allowed   = ["known-identity-status-timestamps", "reconciliation-checkpoint", "session-revocation-outbox", "unclaimed-retention-insert-narrow-update"]
      denied    = ["retention-select-delete-claim-complete", "learning-row-write", "ddl", "lab-validation-state"]
    }
    retention = {
      object_id = azurerm_user_assigned_identity.workload["retention"].principal_id
      allowed   = ["execute-audited-claim-due", "execute-audited-process-due"]
      denied    = ["direct-retention-queue-read-write", "direct-learning-row-read", "eligibility-timestamp-update", "ddl"]
    }
    lab-validation = {
      object_id = azurerm_user_assigned_identity.workload["lab-revalidation"].principal_id
      allowed   = ["active-destination-policy-read", "validation-timestamp-status-failure-counter-safe-error-update"]
      denied    = ["employee-profile", "learning-session", "review", "content-publish", "retention", "ddl"]
    }
    migrator = {
      object_id = azurerm_user_assigned_identity.workload["migration"].principal_id
      allowed   = ["migration-ddl", "migration-backfill"]
      denied    = ["runtime-application-dml", "retention-procedure-execute", "other-database"]
    }
  }

  data_plane_principal_bootstrap = {
    schemaVersion = 1
    redis = {
      bff = azurerm_user_assigned_identity.workload["bff"].principal_id
    }
    postgresql = {
      for role, contract in local.postgresql_data_plane_contract : role => contract.object_id
    }
  }
}

output "data_plane_principal_bootstrap" {
  description = "Identity-only input for scripts/azure/bootstrap-data-principals.sh; contains no credential."
  value       = local.data_plane_principal_bootstrap
}

output "postgresql_data_plane_contract" {
  description = "Reviewed positive and negative object-grant matrix."
  value       = local.postgresql_data_plane_contract
}
