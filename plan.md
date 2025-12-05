# AWS Security Group Drift Detection & Auto-Remediation - Build Plan

## Project Overview
Real-time drift detection system that monitors a specific AWS Security Group and automatically removes unauthorized rules using AWS Lambda, EventBridge, CloudTrail, and Terraform.

---

## Configuration Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| **AWS Region** | eu-west-2 | London region |
| **Notifications** | Both SNS (email) + Slack webhook | Dual notification channels |
| **Security Group** | Placeholder variable | `REPLACE_WITH_YOUR_SG_ID` |
| **Baseline Storage** | S3 bucket | JSON file with baseline rules |
| **CloudTrail** | Existing trail | Using pre-configured CloudTrail |
| **Terraform Backend** | S3 | Remote state management |
| **Baseline Rules** | SSH (specific IP) + HTTPS (0.0.0.0/0) | Configurable via comments |
| **Slack Webhook** | Placeholder in SSM | `REPLACE_WITH_YOUR_WEBHOOK_URL` |

---

## Project Structure

```
drift/
├── terraform/
│   ├── main.tf                    # Root module configuration
│   ├── variables.tf               # Input variables with descriptions
│   ├── outputs.tf                 # Outputs for resources
│   ├── provider.tf                # AWS provider config
│   ├── backend.tf                 # S3 backend configuration
│   ├── modules/
│   │   ├── eventbridge/
│   │   │   ├── main.tf           # EventBridge rule + target
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── lambda/
│   │   │   ├── main.tf           # Lambda function + IAM role
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── storage/
│   │   │   ├── main.tf           # S3 bucket for baseline
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── notifications/
│   │   │   ├── main.tf           # SNS topic + Slack webhook SSM
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   └── security-group/
│   │       ├── main.tf           # Managed Security Group
│   │       ├── variables.tf
│   │       └── outputs.tf
│   └── terraform.tfvars.example  # Example variable values
├── lambda/
│   ├── drift_detector.py         # Main Lambda handler
│   ├── requirements.txt          # Python dependencies
│   └── tests/
│       └── test_drift_detector.py # Unit tests (optional)
├── scripts/
│   └── export_baseline.py        # Export SG baseline to S3
└── README.md                      # Deployment instructions
```

---

## Build Phases

### **Phase 1: Project Setup** ✅
- [x] Create directory structure
- [x] Initialize Terraform configuration
- [x] Set up backend configuration for S3

### **Phase 2: Terraform Infrastructure Development**

#### 2.1 Storage Module (S3 for Baseline)
- Create S3 bucket with versioning
- Enable encryption (AES-256)
- Set bucket policy for Lambda access
- Export baseline rules as JSON

#### 2.2 EventBridge Module
- Create EventBridge rule targeting CloudTrail events
- Filter for specific Security Group ID
- Event pattern for `AuthorizeSecurityGroupIngress` and `AuthorizeSecurityGroupEgress`
- Target: Lambda function

#### 2.3 Lambda Module
- Package Python code with dependencies
- Create Lambda function (Python 3.12)
- IAM role with least-privilege permissions:
  - Read from S3 (baseline)
  - Read CloudTrail events
  - Describe/Revoke SG rules (EC2 API)
  - Publish to SNS
  - Read SSM parameters (Slack webhook)
  - CloudWatch Logs
- Environment variables (S3 bucket, SG ID, SNS topic)

#### 2.4 Notifications Module
- SNS topic for email alerts
- Email subscription (placeholder)
- SSM SecureString for Slack webhook URL
- Dead Letter Queue (optional)

#### 2.5 Security Group Module (Example/Managed)
- Create example Security Group with baseline rules
- Export rules to S3 baseline file
- Output SG ID for easy reference

### **Phase 3: Lambda Function Development**

#### 3.1 Core Functions
```python
- load_baseline_from_s3()          # Read JSON baseline from S3
- get_current_sg_rules()           # Fetch current SG state via boto3
- compare_rules()                  # Identify drift (unauthorized rules)
- revoke_unauthorized_rules()      # Remove ingress/egress rules
- extract_user_identity()          # Parse CloudTrail event
- send_notifications()             # Send to SNS + Slack
- lambda_handler()                 # Main entry point
```

#### 3.2 Key Logic
- Idempotent rule comparison (handle duplicates)
- Graceful error handling with retries
- Detailed CloudWatch logging
- Extract: rule details, user ARN, timestamp

### **Phase 4: Integration & Testing**

#### 4.1 Deployment Steps
1. Update `terraform.tfvars` with your values
2. Configure S3 backend in `backend.tf`
3. Run `terraform init`
4. Run `terraform plan`
5. Run `terraform apply`
6. Export baseline: `python scripts/export_baseline.py`
7. Manually add unauthorized rule to SG
8. Verify auto-remediation in CloudWatch Logs
9. Check email/Slack for notification

#### 4.2 Testing Scenarios
- ✅ Add unauthorized ingress rule → Should be removed
- ✅ Add unauthorized egress rule → Should be removed
- ✅ Add baseline-compliant rule → Should NOT be removed
- ✅ Verify notification includes user identity
- ✅ Test Lambda retries on transient failures

---

## Placeholders to Replace

| Placeholder | Location | Action Required |
|-------------|----------|-----------------|
| `REPLACE_WITH_YOUR_SG_ID` | `terraform.tfvars` | Add your Security Group ID |
| `REPLACE_WITH_YOUR_WEBHOOK_URL` | AWS Console → SSM Parameter | Update SSM parameter after deployment |
| `your-email@example.com` | `terraform.tfvars` | Add your email for SNS subscription |
| `your-s3-backend-bucket` | `backend.tf` | S3 bucket for Terraform state |
| `your-account-id` | Various IAM policies | AWS account ID (auto-detected in code) |

---

## Baseline Rules Structure (S3 JSON)

```json
{
  "security_group_id": "sg-xxxxxxxxx",
  "baseline_rules": {
    "ingress": [
      {
        "IpProtocol": "tcp",
        "FromPort": 22,
        "ToPort": 22,
        "IpRanges": [{"CidrIp": "203.0.113.0/24"}]  # CHANGE: Your IP range
      },
      {
        "IpProtocol": "tcp",
        "FromPort": 443,
        "ToPort": 443,
        "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
      }
    ],
    "egress": [
      {
        "IpProtocol": "-1",
        "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
      }
    ]
  }
}
```

---

## IAM Permissions Summary (Lambda Role)

```
ec2:DescribeSecurityGroups
ec2:RevokeSecurityGroupIngress
ec2:RevokeSecurityGroupEgress
s3:GetObject (baseline bucket)
sns:Publish
ssm:GetParameter (Slack webhook)
logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
```

---

## Cost Estimate (Monthly)

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Lambda | ~100 invocations/month | < $0.01 |
| EventBridge | Rule + events | < $0.01 |
| S3 | 1 small JSON file | < $0.01 |
| SNS | Email notifications | < $0.01 |
| CloudWatch Logs | 1 MB/month | < $0.01 |
| **Total** | | **~$0.05/month** |

*Note: CloudTrail costs excluded (already exists)*

---

## Deployment Timeline

- **Phase 1-2**: 2 hours (Terraform infrastructure)
- **Phase 3**: 1.5 hours (Lambda development)
- **Phase 4**: 30 minutes (Testing & validation)
- **Total**: ~4 hours

---

## Success Criteria

✅ EventBridge successfully triggers Lambda on SG modifications  
✅ Lambda correctly identifies unauthorized rules  
✅ Unauthorized rules are automatically removed within 30 seconds  
✅ Notifications sent to both email and Slack  
✅ User identity captured from CloudTrail event  
✅ No false positives (baseline rules remain intact)  
✅ All operations logged in CloudWatch

---

## Next Steps

1. ✅ Review and approve this plan
2. Generate complete Terraform code
3. Generate complete Lambda Python code
4. Create deployment scripts
5. Generate comprehensive README with deployment instructions

---

**Generated**: 5 December 2025  
**Project**: AWS Security Group Drift Detector  
**Region**: eu-west-2 (London)
