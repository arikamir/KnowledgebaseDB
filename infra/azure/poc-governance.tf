# This file exists only to make the explicitly approved single-administrator
# technical PoC deployable. These groups preserve scoped assignments, but their
# common owner means they are not separation-of-duties evidence and cannot
# satisfy T194 or protected delivery.
resource "azuread_group" "poc_governance" {
  for_each = var.technical_poc_mode ? toset([
    "delivery-operators",
    "evidence-hold-managers",
    "platform-bootstrap",
    "security-reviewers",
  ]) : toset([])

  display_name     = "DevOps Career PoC ${title(replace(each.key, "-", " "))}"
  security_enabled = true
  owners           = [data.azuread_client_config.current.object_id]
  members          = [data.azuread_client_config.current.object_id]
}

locals {
  effective_postgresql_bootstrap_admin_object_id   = var.technical_poc_mode ? azuread_group.poc_governance["platform-bootstrap"].object_id : var.postgresql_bootstrap_admin_object_id
  effective_postgresql_bootstrap_admin_name        = var.technical_poc_mode ? azuread_group.poc_governance["platform-bootstrap"].display_name : var.postgresql_bootstrap_admin_name
  effective_delivery_operators_group_object_id     = var.technical_poc_mode ? azuread_group.poc_governance["delivery-operators"].object_id : var.delivery_operators_group_object_id
  effective_security_reviewers_group_object_id     = var.technical_poc_mode ? azuread_group.poc_governance["security-reviewers"].object_id : var.security_reviewers_group_object_id
  effective_evidence_hold_managers_group_object_id = var.technical_poc_mode ? azuread_group.poc_governance["evidence-hold-managers"].object_id : var.evidence_hold_managers_group_object_id
}
