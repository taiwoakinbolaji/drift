Build an AWS real-time drift-detector and auto-remediation system for a specific Security Group. The infrastructure is provisioned using Terraform, and all unauthorized inbound or outbound rules must be automatically removed when added. The system must also send a notification to Slack or email after remediation. Use AWS Lambda (Python), EventBridge, CloudTrail, and Terraform.

Requirements:

Real-time remediation:

Listen for modifications to a specific Security Group using CloudTrail events through EventBridge.

Trigger a Lambda function anytime a rule is added (ingress or egress).

Baseline definition:

The Security Group is managed by Terraform, so the baseline rules must be exported by Terraform into either:

SSM Parameter Store (preferred)

or S3 JSON file

Lambda must read this baseline and compare it to the current state.

Auto-remediation:

Identify any rule NOT in the baseline.

Remove unauthorized inbound or outbound rules using the EC2 API.

No remediation for baseline-compliant rules.

Alerting:

After remediation, send an alert to either SNS → email or Slack webhook.

Include details:

Unauthorized rule detected

Who made the change (from CloudTrail event)

What was removed

Timestamp

Deliverables to generate:
A. Terraform code for:

CloudTrail (if not already present)

EventBridge rule with proper filtering for the target SG

SSM/S3 baseline storage

Lambda function + IAM role

SNS topic (optional)

Slack webhook stored as SSM SecureString (optional)

B. Lambda function code (Python 3.12):

Read baseline (SSM or S3)

Get current SG rules

Compare SG rules to baseline

Remove unauthorized ingress/egress rules

Extract user identity from the CloudTrail event

Send alert to Slack or SNS

Log all operations

C. Explanation of file structure, Terraform variables/outputs, and deployment steps.

Coding guidelines:

Use least-privilege IAM for the Lambda role.

Terraform code must be fully functional and reference variables cleanly.

Lambda should be idempotent and safe for retries.

Include helpful comments explaining critical logic (comparison and revocation).

Avoid hard-coding SG IDs; use Terraform outputs.

Generate the complete solution end-to-end.
