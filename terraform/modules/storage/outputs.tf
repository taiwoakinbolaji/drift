output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.baseline.id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.baseline.arn
}

output "baseline_key" {
  description = "S3 key for the baseline JSON file"
  value       = "baseline/security-group-baseline.json"
}
