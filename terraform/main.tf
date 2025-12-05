# Main Terraform configuration for Security Group Drift Detector
# This orchestrates all modules to create the complete drift detection system

locals {
  common_tags = merge(
    var.tags,
    {
      Project     = var.project_name
      Environment = var.environment
    }
  )
}

# Storage Module - S3 bucket for baseline Security Group rules
module "storage" {
  source = "./modules/storage"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  tags         = local.common_tags
}

# Notifications Module - SNS topic and Slack webhook configuration
module "notifications" {
  source = "./modules/notifications"

  project_name        = var.project_name
  environment         = var.environment
  alert_email         = var.alert_email
  slack_webhook_url   = var.slack_webhook_url
  tags                = local.common_tags
}

# Lambda Module - Drift detection function
module "lambda" {
  source = "./modules/lambda"

  project_name                  = var.project_name
  environment                   = var.environment
  aws_region                    = var.aws_region
  monitored_security_group_id   = var.monitored_security_group_id
  baseline_bucket_name          = module.storage.bucket_name
  baseline_bucket_arn           = module.storage.bucket_arn
  baseline_s3_key               = module.storage.baseline_key
  sns_topic_arn                 = module.notifications.sns_topic_arn
  slack_webhook_parameter_name  = module.notifications.slack_webhook_parameter_name
  slack_webhook_parameter_arn   = module.notifications.slack_webhook_parameter_arn
  lambda_timeout                = var.lambda_timeout
  lambda_memory_size            = var.lambda_memory_size
  log_retention_days            = var.enable_cloudwatch_logs_retention
  tags                          = local.common_tags
}

# EventBridge Module - CloudTrail event monitoring
module "eventbridge" {
  source = "./modules/eventbridge"

  project_name                = var.project_name
  environment                 = var.environment
  monitored_security_group_id = var.monitored_security_group_id
  lambda_function_arn         = module.lambda.function_arn
  lambda_function_name        = module.lambda.function_name
  tags                        = local.common_tags
}

# Security Group Module (Optional) - Example managed Security Group with baseline
# Uncomment this module if you want Terraform to create and manage the Security Group
# Otherwise, use your existing Security Group and update the monitored_security_group_id variable

# module "security_group" {
#   source = "./modules/security-group"
#
#   project_name          = var.project_name
#   environment           = var.environment
#   vpc_id                = "vpc-xxxxxxxxx"  # REPLACE with your VPC ID
#   baseline_ssh_cidr     = var.baseline_ssh_cidr
#   enable_https_baseline = var.enable_https_baseline
#   tags                  = local.common_tags
# }
