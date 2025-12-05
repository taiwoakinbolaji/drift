variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "alert_email" {
  description = "Email address for SNS notifications"
  type        = string
}

variable "slack_webhook_url" {
  description = "Slack webhook URL (stored in SSM)"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
