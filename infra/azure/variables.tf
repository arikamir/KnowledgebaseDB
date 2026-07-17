variable "subscription_id" {
  description = "Azure subscription receiving the non-production resources."
  type        = string
}

variable "tenant_id" {
  description = "Microsoft Entra tenant used by workload identities and data-plane authentication."
  type        = string
}

variable "postgresql_bootstrap_admin_object_id" {
  description = "Object ID of the PIM-controlled Platform Operations group used only to bootstrap database roles."
  type        = string
}

variable "postgresql_bootstrap_admin_name" {
  description = "Display name of the PIM-controlled PostgreSQL bootstrap administrator group."
  type        = string
  default     = "DevOps Career Platform Operations"
}

variable "virtual_network_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "aks_subnet_cidr" {
  type    = string
  default = "10.42.0.0/20"
}

variable "private_endpoint_subnet_cidr" {
  type    = string
  default = "10.42.16.0/24"
}

variable "postgresql_subnet_cidr" {
  type    = string
  default = "10.42.17.0/24"
}

variable "managed_redis_sku" {
  description = "Azure Managed Redis SKU; Balanced_B0 is the non-production baseline."
  type        = string
  default     = "Balanced_B0"
}

variable "delivery_operators_group_object_id" {
  description = "Object ID of the separately configured Delivery Operators Microsoft Entra group."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.delivery_operators_group_object_id))
    error_message = "delivery_operators_group_object_id must be a Microsoft Entra object ID."
  }
}

variable "security_reviewers_group_object_id" {
  description = "Object ID of the separately configured Security Reviewers Microsoft Entra group."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.security_reviewers_group_object_id))
    error_message = "security_reviewers_group_object_id must be a Microsoft Entra object ID."
  }
}

variable "evidence_hold_managers_group_object_id" {
  description = "Object ID of the separately configured Evidence Hold Managers Microsoft Entra group."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.evidence_hold_managers_group_object_id))
    error_message = "evidence_hold_managers_group_object_id must be a Microsoft Entra object ID."
  }
}

variable "location" {
  type    = string
  default = "israelcentral"
}

variable "prefix" {
  type    = string
  default = "devopscareer"
  validation {
    condition     = can(regex("^[a-z0-9]{3,16}$", var.prefix))
    error_message = "prefix must contain 3-16 lowercase letters or digits."
  }
}

variable "environment" {
  type    = string
  default = "nonprod"
  validation {
    condition     = contains(["nonprod", "dev", "test", "stage"], var.environment)
    error_message = "This foundation is restricted to non-production environments."
  }
}

variable "node_vm_size" {
  type    = string
  default = "Standard_B2s"
}

variable "node_count" {
  type    = number
  default = 1
}

variable "pilot_public_url" {
  description = "Authoritative public AGC HTTPS URL used by pilot availability tests."
  type        = string
  validation {
    condition     = can(regex("^https://[^/]+$", var.pilot_public_url))
    error_message = "pilot_public_url must be an HTTPS origin without a path."
  }
}
