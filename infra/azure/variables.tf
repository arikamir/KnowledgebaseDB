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

variable "pilot_public_url" {
  description = "Authoritative public AGC HTTPS URL used by pilot availability tests."
  type        = string
  validation {
    condition     = can(regex("^https://[^/]+$", var.pilot_public_url))
    error_message = "pilot_public_url must be an HTTPS origin without a path."
  }
}
