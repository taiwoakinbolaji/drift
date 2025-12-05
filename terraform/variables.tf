variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "sg-drift-detector"
}

# IMPORTANT: Replace with your actual Security Group ID
variable "monitored_security_group_id" {
  description = "The Security Group ID to monitor for drift (e.g., sg-0123456789abcdef0)"
  type        = string
  default     = "REPLACE_WITH_YOUR_SG_ID"  # CHANGE THIS!
}

variable "alert_email" {
  description = "Email address to receive drift notifications"
  type        = string
  default     = "your-email@example.com"  # CHANGE THIS!
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications (will be stored in SSM Parameter Store)"
  type        = string
  default     = "REPLACE_WITH_YOUR_WEBHOOK_URL"  # CHANGE THIS!
  sensitive   = true
}

# Baseline SSH access - CUSTOMIZE THESE VALUES
variable "baseline_ssh_cidr" {
  description = "CIDR block allowed for SSH access in baseline (e.g., your office IP)"
  type        = string
  default     = "203.0.113.0/24"  # CHANGE THIS to your IP range!
}

variable "enable_https_baseline" {
  description = "Enable HTTPS (443) access from anywhere in baseline"
  type        = bool
  default     = true
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

variable "enable_cloudwatch_logs_retention" {
  description = "Number of days to retain Lambda logs in CloudWatch"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
