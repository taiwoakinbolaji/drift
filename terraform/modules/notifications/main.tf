# Notification Module - SNS Topic and Slack Webhook Configuration
# Handles dual notification channels: Email (SNS) and Slack

# SNS Topic for email notifications
resource "aws_sns_topic" "drift_alerts" {
  name         = "${var.project_name}-drift-alerts-${var.environment}"
  display_name = "Security Group Drift Alerts"

  tags = var.tags
}

# SNS Topic Subscription - Email
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.drift_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email

  # Note: Email subscriptions require manual confirmation
  # Check your email after deployment to confirm the subscription
}

# SSM Parameter Store - Slack Webhook URL (SecureString)
resource "aws_ssm_parameter" "slack_webhook" {
  name        = "/${var.project_name}/${var.environment}/slack-webhook-url"
  description = "Slack webhook URL for drift detection alerts"
  type        = "SecureString"
  value       = var.slack_webhook_url

  tags = merge(
    var.tags,
    {
      Name        = "slack-webhook-url"
      Description = "Slack webhook for Security Group drift alerts"
    }
  )

  lifecycle {
    ignore_changes = [value]  # Allow manual updates via AWS Console/CLI
  }
}

# SNS Topic Policy - Allow Lambda to publish
resource "aws_sns_topic_policy" "drift_alerts_policy" {
  arn = aws_sns_topic.drift_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaPublish"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.drift_alerts.arn
      }
    ]
  })
}
