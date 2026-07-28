variable "subscription_id" {
  description = "Azure subscription receiving the non-production resources."
  type        = string
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

variable "delivery_operators_group_object_id" {
  description = "Object ID of the separately configured Delivery Operators Microsoft Entra group."
  type        = string
}

variable "security_reviewers_group_object_id" {
  description = "Object ID of the separately configured Security Reviewers Microsoft Entra group."
  type        = string
}

variable "github_repository" {
  description = "Owner/name of the GitHub repository trusted by the publisher identity."
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must be in owner/name form."
  }
}

variable "github_repository_owner_id" {
  description = "Immutable numeric owner ID from the repository OIDC subject customization."
  type        = string
  validation {
    condition     = can(regex("^[1-9][0-9]*$", var.github_repository_owner_id))
    error_message = "github_repository_owner_id must be a positive numeric GitHub owner ID."
  }
}

variable "github_repository_id" {
  description = "Immutable numeric repository ID from the repository OIDC subject customization."
  type        = string
  validation {
    condition     = can(regex("^[1-9][0-9]*$", var.github_repository_id))
    error_message = "github_repository_id must be a positive numeric GitHub repository ID."
  }
}

variable "github_actions_environment" {
  description = "Protected GitHub environment prefix used for the publisher OIDC subject."
  type        = string
  default     = "nonprod"
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+$", var.github_actions_environment))
    error_message = "github_actions_environment must be a simple environment name."
  }
}
