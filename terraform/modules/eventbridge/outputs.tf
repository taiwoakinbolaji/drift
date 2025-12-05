output "rule_name" {
  description = "Name of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.sg_changes.name
}

output "rule_arn" {
  description = "ARN of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.sg_changes.arn
}
