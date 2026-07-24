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
