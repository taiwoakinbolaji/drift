# S3 Bucket for storing Security Group baseline rules
# Contains the "source of truth" for authorized rules

resource "aws_s3_bucket" "baseline" {
  bucket = "${var.project_name}-baseline-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-baseline-${var.environment}"
      Description = "Storage for Security Group baseline rules"
    }
  )
}

# Enable versioning for baseline bucket
resource "aws_s3_bucket_versioning" "baseline" {
  bucket = aws_s3_bucket.baseline.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "baseline" {
  bucket = aws_s3_bucket.baseline.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "baseline" {
  bucket = aws_s3_bucket.baseline.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy to manage old versions
resource "aws_s3_bucket_lifecycle_configuration" "baseline" {
  bucket = aws_s3_bucket.baseline.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}
