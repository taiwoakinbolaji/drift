#!/usr/bin/env python3
"""
Export Security Group Baseline to S3

This script exports the current state of a Security Group as a baseline JSON file to S3.
Run this after deploying the infrastructure to establish the baseline rules.

Usage:
    python3 export_baseline.py

Requirements:
    - AWS CLI configured with appropriate credentials
    - boto3 installed (pip install boto3)
    - Environment variables or update the constants below
"""

import json
import os
import sys
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Configuration - Update these or set via environment variables
SECURITY_GROUP_ID = os.environ.get('SECURITY_GROUP_ID', 'REPLACE_WITH_YOUR_SG_ID')
BASELINE_BUCKET = os.environ.get('BASELINE_BUCKET', '')  # Will be auto-detected from Terraform
BASELINE_S3_KEY = 'baseline/security-group-baseline.json'
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-2')

# Initialize boto3 clients
ec2_client = boto3.client('ec2', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)


def get_terraform_output(output_name: str) -> str:
    """
    Get Terraform output value
    
    Args:
        output_name: Name of the Terraform output
        
    Returns:
        Output value as string
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ['terraform', 'output', '-raw', output_name],
            capture_output=True,
            text=True,
            cwd='../terraform',
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Warning: Could not get Terraform output '{output_name}': {e}")
        return None


def fetch_security_group_rules(sg_id: str) -> dict:
    """
    Fetch current Security Group rules
    
    Args:
        sg_id: Security Group ID
        
    Returns:
        Dictionary containing ingress and egress rules
    """
    print(f"📡 Fetching rules for Security Group: {sg_id}")
    
    try:
        response = ec2_client.describe_security_groups(GroupIds=[sg_id])
        
        if not response['SecurityGroups']:
            print(f"❌ Error: Security Group {sg_id} not found")
            sys.exit(1)
        
        sg = response['SecurityGroups'][0]
        
        # Extract rules
        rules = {
            'ingress': sg.get('IpPermissions', []),
            'egress': sg.get('IpPermissionsEgress', [])
        }
        
        print(f"✅ Found {len(rules['ingress'])} ingress rules")
        print(f"✅ Found {len(rules['egress'])} egress rules")
        
        return rules
        
    except ClientError as e:
        print(f"❌ Error fetching Security Group: {str(e)}")
        sys.exit(1)


def create_baseline_json(sg_id: str, rules: dict) -> dict:
    """
    Create baseline JSON structure
    
    Args:
        sg_id: Security Group ID
        rules: Dictionary of ingress/egress rules
        
    Returns:
        Baseline JSON dictionary
    """
    baseline = {
        'security_group_id': sg_id,
        'baseline_version': '1.0',
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'baseline_rules': rules,
        'description': 'Baseline Security Group rules for drift detection'
    }
    
    return baseline


def upload_to_s3(bucket: str, key: str, data: dict) -> bool:
    """
    Upload baseline JSON to S3
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        data: Baseline data dictionary
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n📤 Uploading baseline to s3://{bucket}/{key}")
    
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        print(f"✅ Baseline uploaded successfully!")
        return True
        
    except ClientError as e:
        print(f"❌ Error uploading to S3: {str(e)}")
        return False


def print_baseline_summary(baseline: dict):
    """
    Print a summary of the baseline
    
    Args:
        baseline: Baseline dictionary
    """
    print("\n" + "="*60)
    print("📋 BASELINE SUMMARY")
    print("="*60)
    print(f"Security Group ID: {baseline['security_group_id']}")
    print(f"Baseline Version: {baseline['baseline_version']}")
    print(f"Created At: {baseline['created_at']}")
    
    print("\n🔽 INGRESS RULES (Inbound):")
    for i, rule in enumerate(baseline['baseline_rules']['ingress'], 1):
        protocol = rule.get('IpProtocol', 'all')
        from_port = rule.get('FromPort', 'all')
        to_port = rule.get('ToPort', 'all')
        
        cidrs = [r.get('CidrIp', '') for r in rule.get('IpRanges', [])]
        sources = ', '.join(filter(None, cidrs)) or 'none'
        
        print(f"  {i}. Protocol: {protocol}, Ports: {from_port}-{to_port}, Source: {sources}")
    
    print("\n🔼 EGRESS RULES (Outbound):")
    for i, rule in enumerate(baseline['baseline_rules']['egress'], 1):
        protocol = rule.get('IpProtocol', 'all')
        from_port = rule.get('FromPort', 'all')
        to_port = rule.get('ToPort', 'all')
        
        cidrs = [r.get('CidrIp', '') for r in rule.get('IpRanges', [])]
        destinations = ', '.join(filter(None, cidrs)) or 'none'
        
        print(f"  {i}. Protocol: {protocol}, Ports: {from_port}-{to_port}, Destination: {destinations}")
    
    print("="*60 + "\n")


def main():
    """Main function"""
    print("\n" + "="*60)
    print("🚀 AWS SECURITY GROUP BASELINE EXPORTER")
    print("="*60 + "\n")
    
    # Try to get values from Terraform outputs
    global SECURITY_GROUP_ID, BASELINE_BUCKET
    
    if SECURITY_GROUP_ID == 'REPLACE_WITH_YOUR_SG_ID':
        tf_sg_id = get_terraform_output('monitored_security_group_id')
        if tf_sg_id:
            SECURITY_GROUP_ID = tf_sg_id
            print(f"✅ Using Security Group ID from Terraform: {SECURITY_GROUP_ID}")
    
    if not BASELINE_BUCKET:
        tf_bucket = get_terraform_output('baseline_s3_bucket')
        if tf_bucket:
            BASELINE_BUCKET = tf_bucket
            print(f"✅ Using S3 bucket from Terraform: {BASELINE_BUCKET}")
    
    # Validate configuration
    if SECURITY_GROUP_ID == 'REPLACE_WITH_YOUR_SG_ID':
        print("❌ Error: SECURITY_GROUP_ID not set")
        print("   Set via environment variable: export SECURITY_GROUP_ID=sg-xxxxx")
        print("   Or update the script directly")
        sys.exit(1)
    
    if not BASELINE_BUCKET:
        print("❌ Error: BASELINE_BUCKET not set")
        print("   Set via environment variable: export BASELINE_BUCKET=your-bucket-name")
        print("   Or run 'terraform output baseline_s3_bucket' from terraform directory")
        sys.exit(1)
    
    print(f"🎯 Configuration:")
    print(f"   Security Group: {SECURITY_GROUP_ID}")
    print(f"   S3 Bucket: {BASELINE_BUCKET}")
    print(f"   S3 Key: {BASELINE_S3_KEY}")
    print(f"   Region: {AWS_REGION}\n")
    
    # Fetch current rules
    rules = fetch_security_group_rules(SECURITY_GROUP_ID)
    
    # Create baseline
    baseline = create_baseline_json(SECURITY_GROUP_ID, rules)
    
    # Print summary
    print_baseline_summary(baseline)
    
    # Confirm upload
    response = input("📤 Upload this baseline to S3? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("❌ Upload cancelled by user")
        sys.exit(0)
    
    # Upload to S3
    success = upload_to_s3(BASELINE_BUCKET, BASELINE_S3_KEY, baseline)
    
    if success:
        print("\n✅ SUCCESS! Baseline exported and uploaded.")
        print(f"\n📍 Next Steps:")
        print(f"   1. Test drift detection by manually adding a rule to {SECURITY_GROUP_ID}")
        print(f"   2. Check CloudWatch Logs for the Lambda function")
        print(f"   3. Verify the unauthorized rule is automatically removed")
        print(f"   4. Check your email and Slack for notifications")
        print("\n" + "="*60)
        sys.exit(0)
    else:
        print("\n❌ FAILED to upload baseline to S3")
        sys.exit(1)


if __name__ == "__main__":
    main()
