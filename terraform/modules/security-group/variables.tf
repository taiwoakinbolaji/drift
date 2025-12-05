variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the Security Group will be created"
  type        = string
}

variable "baseline_ssh_cidr" {
  description = "CIDR block allowed for SSH access"
  type        = string
}

variable "enable_https_baseline" {
  description = "Enable HTTPS access from anywhere"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
