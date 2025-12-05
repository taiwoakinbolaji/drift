# Lambda Function for Security Group Drift Detection and Auto-Remediation
# Compares current SG rules against baseline and removes unauthorized rules

# CloudWatch Logs Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-drift-detector-${var.environment}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# Package Lambda function code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../../lambda/drift_detector.py"
  output_path = "${path.module}/lambda_function.zip"
}

# Lambda Function
resource "aws_lambda_function" "drift_detector" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-drift-detector-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "drift_detector.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      SECURITY_GROUP_ID            = var.monitored_security_group_id
      BASELINE_BUCKET              = var.baseline_bucket_name
      BASELINE_S3_KEY              = var.baseline_s3_key
      SNS_TOPIC_ARN                = var.sns_topic_arn
      SLACK_WEBHOOK_PARAMETER_NAME = var.slack_webhook_parameter_name
      AWS_REGION                   = var.aws_region
      LOG_LEVEL                    = "INFO"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_custom_policy
  ]

  tags = var.tags
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Attach AWS managed policy for basic Lambda execution (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom IAM Policy for Lambda - Least Privilege
resource "aws_iam_policy" "lambda_custom_policy" {
  name        = "${var.project_name}-lambda-policy-${var.environment}"
  description = "Least-privilege policy for drift detector Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadBaselineFromS3"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "${var.baseline_bucket_arn}/${var.baseline_s3_key}"
      },
      {
        Sid    = "ManageSecurityGroupRules"
        Effect = "Allow"
        Action = [
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSecurityGroupRules",
          "ec2:RevokeSecurityGroupIngress",
          "ec2:RevokeSecurityGroupEgress"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:ResourceTag/ManagedBy" = "Terraform"
          }
        }
      },
      {
        Sid    = "PublishToSNS"
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.sns_topic_arn
      },
      {
        Sid    = "ReadSlackWebhookFromSSM"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = var.slack_webhook_parameter_arn
      }
    ]
  })

  tags = var.tags
}

# Attach custom policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_custom_policy" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_custom_policy.arn
}
