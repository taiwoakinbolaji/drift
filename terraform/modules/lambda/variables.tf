variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "monitored_security_group_id" {
  description = "Security Group ID to monitor"
  type        = string
}

variable "baseline_bucket_name" {
  description = "S3 bucket name containing baseline rules"
  type        = string
}

variable "baseline_bucket_arn" {
  description = "S3 bucket ARN containing baseline rules"
  type        = string
}

variable "baseline_s3_key" {
  description = "S3 key for baseline JSON file"
  type        = string
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for notifications"
  type        = string
}

variable "slack_webhook_parameter_name" {
  description = "SSM parameter name for Slack webhook"
  type        = string
}

variable "slack_webhook_parameter_arn" {
  description = "SSM parameter ARN for Slack webhook"
  type        = string
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 256
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
