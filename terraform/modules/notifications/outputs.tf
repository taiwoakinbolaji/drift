output "sns_topic_arn" {
  description = "ARN of the SNS topic"
  value       = aws_sns_topic.drift_alerts.arn
}

output "slack_webhook_parameter_name" {
  description = "SSM parameter name for Slack webhook"
  value       = aws_ssm_parameter.slack_webhook.name
}

output "slack_webhook_parameter_arn" {
  description = "SSM parameter ARN for Slack webhook"
  value       = aws_ssm_parameter.slack_webhook.arn
}
