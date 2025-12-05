# EventBridge Rule to monitor Security Group changes via CloudTrail
# Triggers Lambda function when ingress/egress rules are added

resource "aws_cloudwatch_event_rule" "sg_changes" {
  name        = "${var.project_name}-sg-changes-${var.environment}"
  description = "Detect Security Group rule additions for ${var.monitored_security_group_id}"

  # Event pattern to capture AuthorizeSecurityGroup API calls for the specific SG
  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["AWS API Call via CloudTrail"]
    detail = {
      eventSource = ["ec2.amazonaws.com"]
      eventName = [
        "AuthorizeSecurityGroupIngress",
        "AuthorizeSecurityGroupEgress"
      ]
      requestParameters = {
        groupId = [var.monitored_security_group_id]
      }
    }
  })

  tags = var.tags
}

# EventBridge Target - Lambda function
resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.sg_changes.name
  target_id = "DriftDetectorLambda"
  arn       = var.lambda_function_arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sg_changes.arn
}
