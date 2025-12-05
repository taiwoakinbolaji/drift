# S3 Backend Configuration for Terraform State
# 
# IMPORTANT: Before running terraform init, create the S3 bucket and DynamoDB table:
# 
# aws s3api create-bucket \
#   --bucket YOUR-TERRAFORM-STATE-BUCKET-NAME \
#   --region eu-west-2 \
#   --create-bucket-configuration LocationConstraint=eu-west-2
#
# aws s3api put-bucket-versioning \
#   --bucket YOUR-TERRAFORM-STATE-BUCKET-NAME \
#   --versioning-configuration Status=Enabled
#
# aws dynamodb create-table \
#   --table-name terraform-state-lock \
#   --attribute-definitions AttributeName=LockID,AttributeType=S \
#   --key-schema AttributeName=LockID,KeyType=HASH \
#   --billing-mode PAY_PER_REQUEST \
#   --region eu-west-2

terraform {
  backend "s3" {
    bucket         = "YOUR-TERRAFORM-STATE-BUCKET-NAME"  # REPLACE: Your S3 bucket name
    key            = "drift-detector/terraform.tfstate"
    region         = "eu-west-2"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
