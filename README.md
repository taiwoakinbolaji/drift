# AWS Security Group Drift Detector & Auto-Remediation System

A real-time infrastructure drift detection and auto-remediation system for AWS Security Groups using Terraform, Lambda, EventBridge, and CloudTrail.

## 🎯 Overview

This system automatically detects and removes unauthorized Security Group rules in real-time. When someone adds a rule that doesn't match the baseline configuration, the system:

1. **Detects** the change via CloudTrail and EventBridge
2. **Compares** against the baseline stored in S3
3. **Removes** unauthorized rules automatically
4. **Notifies** via email (SNS) and Slack with full details

## 🏗️ Architecture

```
CloudTrail → EventBridge → Lambda → EC2 API
                              ↓
                         S3 (Baseline)
                              ↓
                      SNS + Slack (Alerts)
```

## 📋 Features

- ✅ Real-time drift detection via CloudTrail events
- ✅ Automatic remediation (rule removal)
- ✅ Dual notification channels (Email + Slack)
- ✅ User identity tracking from CloudTrail
- ✅ S3-based baseline configuration
- ✅ Least-privilege IAM policies
- ✅ Comprehensive CloudWatch logging
- ✅ Idempotent and retry-safe

## 🚀 Prerequisites

- **AWS CLI** configured with appropriate credentials
- **Terraform** >= 1.5.0
- **Python** 3.12+ (for scripts)
- **AWS Account** with permissions to create:
  - Lambda functions
  - EventBridge rules
  - S3 buckets
  - SNS topics
  - IAM roles/policies
  - SSM parameters
- **Existing CloudTrail** trail (must be configured and logging API events)

## 📦 Project Structure

```
drift/
├── terraform/                 # Infrastructure as Code
│   ├── main.tf               # Root module
│   ├── variables.tf          # Input variables
│   ├── outputs.tf            # Output values
│   ├── provider.tf           # AWS provider config
│   ├── backend.tf            # S3 backend (state storage)
│   ├── terraform.tfvars.example  # Example variables
│   └── modules/
│       ├── eventbridge/      # CloudTrail event monitoring
│       ├── lambda/           # Drift detection function
│       ├── storage/          # S3 baseline storage
│       ├── notifications/    # SNS + Slack webhooks
│       └── security-group/   # Optional managed SG
├── lambda/
│   ├── drift_detector.py     # Main Lambda function
│   └── requirements.txt      # Python dependencies
├── scripts/
│   └── export_baseline.py    # Baseline export utility
├── plan.md                   # Detailed build plan
└── README.md                 # This file
```

## 🛠️ Installation & Deployment

### Step 1: Configure Variables

Copy the example variables file and update with your values:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and replace:

```hcl
# REQUIRED: Your Security Group ID
monitored_security_group_id = "sg-0123456789abcdef0"  # CHANGE THIS!

# REQUIRED: Your email for notifications
alert_email = "your-email@example.com"  # CHANGE THIS!

# REQUIRED: Your Slack webhook (or update in SSM later)
slack_webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# REQUIRED: Your IP for SSH baseline
baseline_ssh_cidr = "203.0.113.0/24"  # CHANGE THIS to your IP!
```

### Step 2: Configure Backend (Terraform State)

Edit `backend.tf` and update the S3 bucket name:

```hcl
bucket = "YOUR-TERRAFORM-STATE-BUCKET-NAME"  # REPLACE THIS
```

Create the S3 bucket and DynamoDB table for state locking:

```bash
# Create S3 bucket for state
aws s3api create-bucket \
  --bucket YOUR-TERRAFORM-STATE-BUCKET-NAME \
  --region eu-west-2 \
  --create-bucket-configuration LocationConstraint=eu-west-2

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket YOUR-TERRAFORM-STATE-BUCKET-NAME \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-2
```

### Step 3: Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Review the execution plan
terraform plan

# Apply the configuration
terraform apply
```

Review the output and type `yes` to confirm deployment.

### Step 4: Confirm Email Subscription

After deployment, check your email inbox for an SNS subscription confirmation. Click the confirmation link to enable email notifications.

### Step 5: Update Slack Webhook (if needed)

If you used a placeholder for the Slack webhook, update it now:

```bash
aws ssm put-parameter \
  --name "/sg-drift-detector/prod/slack-webhook-url" \
  --value "https://hooks.slack.com/services/YOUR/ACTUAL/WEBHOOK" \
  --type "SecureString" \
  --overwrite \
  --region eu-west-2
```

### Step 6: Export Baseline

Export the current Security Group rules as the baseline:

```bash
cd ../scripts
python3 export_baseline.py
```

This will:
- Fetch current Security Group rules
- Display a summary
- Upload to S3 as the baseline configuration

## 🧪 Testing

### Test Drift Detection

1. **Add an unauthorized rule** to your Security Group:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 3389 \
  --cidr 0.0.0.0/0 \
  --region eu-west-2
```

2. **Check CloudWatch Logs** (within 30 seconds):

```bash
aws logs tail /aws/lambda/sg-drift-detector-drift-detector-prod --follow
```

3. **Verify remediation**:
   - The unauthorized rule should be automatically removed
   - Check your email for notification
   - Check Slack channel for alert

4. **Verify the rule is gone**:

```bash
aws ec2 describe-security-groups \
  --group-ids sg-0123456789abcdef0 \
  --region eu-west-2
```

## 📊 Monitoring

### CloudWatch Logs

View Lambda execution logs:

```bash
aws logs tail /aws/lambda/sg-drift-detector-drift-detector-prod --follow
```

### CloudWatch Metrics

Monitor Lambda invocations:
- Invocations
- Errors
- Duration
- Throttles

### EventBridge Monitoring

Check EventBridge rule metrics:
- Invocations
- Failed invocations
- Matched events

## 🔧 Configuration

### Customizing Baseline Rules

To update the baseline after making approved changes:

1. Update the Security Group with approved rules
2. Re-run the export script:
   ```bash
   cd scripts
   python3 export_baseline.py
   ```
3. Confirm the upload

### Adding More Rules to Baseline

Edit your Security Group in Terraform (if using the security-group module):

```hcl
# terraform/modules/security-group/main.tf

resource "aws_vpc_security_group_ingress_rule" "custom_rule" {
  security_group_id = aws_security_group.managed.id
  description       = "Allow custom port"
  
  cidr_ipv4   = "10.0.0.0/8"
  from_port   = 8080
  to_port     = 8080
  ip_protocol = "tcp"
}
```

Then apply and re-export:

```bash
terraform apply
cd ../scripts
python3 export_baseline.py
```

## 🔐 Security Considerations

### IAM Permissions

The Lambda function uses **least-privilege** permissions:

- ✅ Read S3 baseline (specific bucket/key only)
- ✅ Describe Security Groups
- ✅ Revoke SG rules (with condition on ManagedBy=Terraform tag)
- ✅ Publish to SNS
- ✅ Read SSM parameters (Slack webhook only)
- ✅ CloudWatch Logs

### Data Encryption

- ✅ S3 baseline encrypted with AES-256
- ✅ Slack webhook stored as SSM SecureString (KMS encrypted)
- ✅ CloudWatch Logs encrypted

### Network Security

- ✅ Lambda function doesn't require VPC access
- ✅ All AWS API calls over TLS/HTTPS

## 💰 Cost Estimate

Approximate monthly costs (assuming ~100 drift events/month):

| Service | Cost |
|---------|------|
| Lambda | < $0.01 |
| EventBridge | < $0.01 |
| S3 | < $0.01 |
| SNS | < $0.01 |
| CloudWatch Logs | < $0.01 |
| **Total** | **~$0.05/month** |

*CloudTrail costs excluded (assuming existing trail)*

## 🐛 Troubleshooting

### Issue: Lambda not triggered

**Symptoms**: No CloudWatch logs when SG rules are added

**Solutions**:
1. Verify CloudTrail is enabled and logging API events
2. Check EventBridge rule is enabled
3. Verify the Security Group ID in EventBridge rule matches your SG
4. Check Lambda execution role has proper permissions

### Issue: Rules not removed

**Symptoms**: Drift detected but rules remain

**Solutions**:
1. Check Lambda CloudWatch logs for errors
2. Verify Lambda IAM role has `ec2:RevokeSecurityGroup*` permissions
3. Ensure Security Group has `ManagedBy=Terraform` tag
4. Check if rule matches the required format

### Issue: No notifications received

**Symptoms**: Drift remediated but no email/Slack alerts

**Solutions**:
1. **Email**: Confirm SNS subscription in your email
2. **Slack**: Verify webhook URL in SSM Parameter Store
3. Check Lambda logs for notification errors
4. Verify SNS topic ARN in Lambda environment variables

### Issue: Baseline not found

**Symptoms**: Lambda error "Failed to load baseline from S3"

**Solutions**:
1. Run `python3 scripts/export_baseline.py` to create baseline
2. Verify S3 bucket name in Lambda environment variables
3. Check Lambda IAM role has `s3:GetObject` permission for baseline bucket

## 📚 Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/)
- [CloudTrail Documentation](https://docs.aws.amazon.com/cloudtrail/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

## 🤝 Contributing

To enhance this project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is provided as-is for educational and operational purposes.

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review CloudWatch Logs for detailed error messages
3. Verify all configuration values in `terraform.tfvars`

---

**Last Updated**: 5 December 2025  
**Region**: eu-west-2 (London)  
**Terraform Version**: >= 1.5.0  
**Python Version**: 3.12
