output "lambda_function_arn" {
  description = "ARN of the drift detector Lambda function"
  value       = module.lambda.function_arn
}

output "lambda_function_name" {
  description = "Name of the drift detector Lambda function"
  value       = module.lambda.function_name
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule monitoring Security Group changes"
  value       = module.eventbridge.rule_name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for email notifications"
  value       = module.notifications.sns_topic_arn
}

output "baseline_s3_bucket" {
  description = "S3 bucket storing the baseline Security Group rules"
  value       = module.storage.bucket_name
}

output "baseline_s3_key" {
  description = "S3 key (path) for the baseline JSON file"
  value       = module.storage.baseline_key
}

output "monitored_security_group_id" {
  description = "The Security Group ID being monitored"
  value       = var.monitored_security_group_id
}

output "slack_webhook_ssm_parameter" {
  description = "SSM Parameter Store name containing Slack webhook URL"
  value       = module.notifications.slack_webhook_parameter_name
}

output "deployment_instructions" {
  description = "Next steps after deployment"
  value       = <<-EOT
    
    ========================================
    DEPLOYMENT SUCCESSFUL! 
    ========================================
    
    Next Steps:
    
    1. Update Slack Webhook URL in SSM Parameter Store:
       aws ssm put-parameter \
         --name "${module.notifications.slack_webhook_parameter_name}" \
         --value "YOUR_ACTUAL_SLACK_WEBHOOK_URL" \
         --type "SecureString" \
         --overwrite \
         --region ${var.aws_region}
    
    2. Confirm SNS email subscription:
       Check your email (${var.alert_email}) and confirm the SNS subscription
    
    3. Export baseline rules to S3:
       cd ../scripts
       python3 export_baseline.py
    
    4. Test the drift detection:
       - Manually add an unauthorized rule to Security Group: ${var.monitored_security_group_id}
       - Check CloudWatch Logs: /aws/lambda/${module.lambda.function_name}
       - Verify the rule is automatically removed
       - Check email and Slack for notifications
    
    Monitored Security Group: ${var.monitored_security_group_id}
    Lambda Function: ${module.lambda.function_name}
    S3 Baseline: s3://${module.storage.bucket_name}/${module.storage.baseline_key}
    
    ========================================
  EOT
}
