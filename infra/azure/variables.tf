variable "subscription_id" {
  description = "Azure subscription receiving the non-production resources."
  type        = string
}

variable "tenant_id" {
  description = "Microsoft Entra tenant used by workload identities and data-plane authentication."
  type        = string
}

variable "poc_operator_source_cidrs" {
  description = "Temporary operator CIDRs allowed to reach the Key Vault and AKS API public endpoints in technical PoC mode."
  type        = list(string)
  default     = []
  validation {
    condition = !var.technical_poc_mode || (
      length(var.poc_operator_source_cidrs) > 0 &&
      alltrue([for cidr in var.poc_operator_source_cidrs : can(cidrnetmask(cidr))])
    )
    error_message = "poc_operator_source_cidrs must contain at least one valid CIDR in technical PoC mode."
  }
}

variable "aks_api_server_authorized_ip_ranges" {
  description = "Reviewed source CIDRs allowed to reach the public AKS API server. Null preserves the formal platform default; technical PoC mode falls back to poc_operator_source_cidrs."
  type        = list(string)
  default     = null
  nullable    = true
  validation {
    condition = var.aks_api_server_authorized_ip_ranges == null || (
      length(var.aks_api_server_authorized_ip_ranges) > 0 &&
      alltrue([for cidr in var.aks_api_server_authorized_ip_ranges : can(cidrnetmask(cidr))])
    )
    error_message = "aks_api_server_authorized_ip_ranges must be null or contain at least one valid CIDR."
  }
}

variable "postgresql_bootstrap_admin_object_id" {
  description = "Object ID of the PIM-controlled Platform Operations group used only to bootstrap database roles."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = var.technical_poc_mode || (var.postgresql_bootstrap_admin_object_id != null && can(regex("^[0-9a-fA-F-]{36}$", var.postgresql_bootstrap_admin_object_id)))
    error_message = "postgresql_bootstrap_admin_object_id is required outside technical PoC mode."
  }
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
  default     = null
  nullable    = true
  validation {
    condition     = var.technical_poc_mode || (var.browser_dns_zone_name != null && trimspace(var.browser_dns_zone_name) != "")
    error_message = "browser_dns_zone_name is required outside technical PoC mode."
  }
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
  default     = null
  nullable    = true
  validation {
    condition     = var.technical_poc_mode || (var.public_certificate_issuer_name != null && !contains(["Self", "Unknown", ""], var.public_certificate_issuer_name))
    error_message = "public_certificate_issuer_name must name a configured browser-trusted Key Vault issuer."
  }
}

variable "private_core_certificate_issuer_name" {
  description = "Preconfigured Key Vault private-CA issuer for the core server certificate."
  type        = string
  validation {
    condition     = (var.technical_poc_mode && var.private_core_certificate_issuer_name == "Self") || !contains(["Self", "Unknown", ""], var.private_core_certificate_issuer_name)
    error_message = "private_core_certificate_issuer_name must name the configured private CA issuer."
  }
}

variable "technical_poc_mode" {
  description = "Enable the explicitly non-release single-admin PoC path. This never satisfies T194 or protected delivery."
  type        = bool
  default     = false
}

variable "delivery_evidence_policy_state" {
  description = "Account-level evidence policy state. Azure requires Unlocked at creation; formal Platform Operations changes it to Locked in a reviewed second apply."
  type        = string
  default     = "Unlocked"
  validation {
    condition     = contains(["Unlocked", "Locked"], var.delivery_evidence_policy_state) && (!var.technical_poc_mode || var.delivery_evidence_policy_state == "Unlocked")
    error_message = "delivery_evidence_policy_state must be Unlocked or Locked, and technical PoC mode must remain Unlocked."
  }
}

variable "poc_public_hostname" {
  description = "Two-phase sslip.io hostname derived from the provisioned AGC frontend IP. Use pending.invalid for the infrastructure-only first phase."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = !var.technical_poc_mode || (var.poc_public_hostname != null && can(regex("^[a-z0-9.-]+$", var.poc_public_hostname)))
    error_message = "poc_public_hostname is required in technical PoC mode and must be a lowercase DNS hostname."
  }
}

variable "poc_acme_contact_email" {
  description = "Contact email registered with the PoC Let's Encrypt ACME account."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = !var.technical_poc_mode || (var.poc_acme_contact_email != null && can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.poc_acme_contact_email)))
    error_message = "poc_acme_contact_email must be a valid email address in technical PoC mode."
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
  default     = null
  nullable    = true
  validation {
    condition     = var.technical_poc_mode || (var.delivery_operators_group_object_id != null && can(regex("^[0-9a-fA-F-]{36}$", var.delivery_operators_group_object_id)))
    error_message = "delivery_operators_group_object_id must be a Microsoft Entra object ID."
  }
}

variable "security_reviewers_group_object_id" {
  description = "Object ID of the separately configured Security Reviewers Microsoft Entra group."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = var.technical_poc_mode || (var.security_reviewers_group_object_id != null && can(regex("^[0-9a-fA-F-]{36}$", var.security_reviewers_group_object_id)))
    error_message = "security_reviewers_group_object_id must be a Microsoft Entra object ID."
  }
}

variable "evidence_hold_managers_group_object_id" {
  description = "Object ID of the separately configured Evidence Hold Managers Microsoft Entra group."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = var.technical_poc_mode || (var.evidence_hold_managers_group_object_id != null && can(regex("^[0-9a-fA-F-]{36}$", var.evidence_hold_managers_group_object_id)))
    error_message = "evidence_hold_managers_group_object_id must be a Microsoft Entra object ID."
  }
}

variable "approved_machine_consumers" {
  description = "Reviewed machine-client inventory; every entry receives only its declared core API roles."
  type = map(object({
    display_name = string
    roles        = set(string)
  }))

  validation {
    condition     = length(var.approved_machine_consumers) > 0
    error_message = "approved_machine_consumers must contain at least one reviewed machine client."
  }

  validation {
    condition = alltrue([
      for consumer in values(var.approved_machine_consumers) :
      length(consumer.roles) > 0 && length(setsubtract(consumer.roles, toset([
        "CareerAgent.Roadmap.Generate",
        "CareerAgent.Guidance.Read",
        "CareerAgent.Progress.Write",
        "CareerAgent.Health.Read",
      ]))) == 0
    ])
    error_message = "Each machine client must declare a nonempty subset of the four approved CareerAgent application roles."
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
  description = "Number of system nodes. Two Standard_B2s nodes are the non-production baseline so the application and Argo CD control plane fit within the AKS pod and CPU capacity."
  type        = number
  default     = 2
  validation {
    condition     = var.node_count >= 2
    error_message = "node_count must be at least 2 for the application plus Argo CD control plane."
  }
}

variable "pilot_public_url" {
  description = "Authoritative public AGC HTTPS URL used by pilot availability tests."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = var.technical_poc_mode || (var.pilot_public_url != null && can(regex("^https://[^/]+$", var.pilot_public_url)))
    error_message = "pilot_public_url must be an HTTPS origin without a path."
  }
}

variable "github_repository" {
  description = "Owner/name of the GitHub repository trusted by Actions delivery identities."
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must be in owner/name form."
  }
}

variable "github_repository_owner_id" {
  description = "Immutable GitHub owner ID retained in reviewed infrastructure receipts; it is metadata, not part of GitHub's emitted OIDC subject."
  type        = string
  validation {
    condition     = can(regex("^[1-9][0-9]*$", var.github_repository_owner_id))
    error_message = "github_repository_owner_id must be a positive numeric GitHub owner ID."
  }
}

variable "github_repository_id" {
  description = "Immutable GitHub repository ID retained in reviewed infrastructure receipts; it is metadata, not part of GitHub's emitted OIDC subject."
  type        = string
  validation {
    condition     = can(regex("^[1-9][0-9]*$", var.github_repository_id))
    error_message = "github_repository_id must be a positive numeric GitHub repository ID."
  }
}

variable "github_actions_environment" {
  description = "Protected GitHub environment name used in the Actions OIDC subject."
  type        = string
  default     = "nonprod"
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+$", var.github_actions_environment))
    error_message = "github_actions_environment must be a simple environment name."
  }
}
