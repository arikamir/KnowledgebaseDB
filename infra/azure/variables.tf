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

variable "application_gateway_for_containers_subnet_cidr" {
  description = "Dedicated /24 subnet for the single Application Gateway for Containers deployment."
  type        = string
  default     = "10.42.18.0/24"
  validation {
    condition     = can(cidrnetmask(var.application_gateway_for_containers_subnet_cidr)) && endswith(var.application_gateway_for_containers_subnet_cidr, "/24")
    error_message = "application_gateway_for_containers_subnet_cidr must be a valid /24 CIDR."
  }
}

variable "browser_dns_zone_name" {
  description = "Authoritative public DNS zone for the browser gateway."
  type        = string
}

variable "browser_gateway_source_cidrs" {
  description = "Reviewed public source CIDRs allowed to reach the AGC HTTPS frontend."
  type        = list(string)
  validation {
    condition     = length(var.browser_gateway_source_cidrs) > 0 && alltrue([for cidr in var.browser_gateway_source_cidrs : can(cidrnetmask(cidr))])
    error_message = "browser_gateway_source_cidrs must contain at least one valid reviewed CIDR."
  }
}

variable "browser_dns_record_name" {
  description = "Relative record name for the browser gateway."
  type        = string
  default     = "career-agent"
}

variable "private_core_dns_zone_name" {
  description = "Private DNS trust domain for the core machine endpoint."
  type        = string
  default     = "career-agent.internal"
}

variable "private_core_load_balancer_ip" {
  description = "Reserved AKS-subnet address used by the internal core LoadBalancer."
  type        = string
  default     = "10.42.0.100"
}

variable "public_certificate_issuer_name" {
  description = "Preconfigured Key Vault issuer for a browser-trusted public certificate."
  type        = string
  validation {
    condition     = !contains(["Self", "Unknown", ""], var.public_certificate_issuer_name)
    error_message = "public_certificate_issuer_name must name a configured browser-trusted Key Vault issuer."
  }
}

variable "private_core_certificate_issuer_name" {
  description = "Preconfigured Key Vault private-CA issuer for the core server certificate."
  type        = string
  validation {
    condition     = !contains(["Self", "Unknown", ""], var.private_core_certificate_issuer_name)
    error_message = "private_core_certificate_issuer_name must name the configured private CA issuer."
  }
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
