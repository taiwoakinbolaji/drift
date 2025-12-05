"""
AWS Security Group Drift Detector and Auto-Remediation Lambda Function

This function:
1. Receives CloudTrail events from EventBridge when SG rules are added
2. Loads baseline rules from S3
3. Compares current SG state against baseline
4. Removes unauthorized rules (ingress/egress)
5. Sends notifications to SNS (email) and Slack
6. Logs all operations to CloudWatch

Author: AWS Drift Detection System
Version: 1.0
Python: 3.12
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
import urllib3

# Initialize AWS clients
ec2_client = boto3.client('ec2')
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
ssm_client = boto3.client('ssm')
http = urllib3.PoolManager()

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Environment variables
SECURITY_GROUP_ID = os.environ['SECURITY_GROUP_ID']
BASELINE_BUCKET = os.environ['BASELINE_BUCKET']
BASELINE_S3_KEY = os.environ['BASELINE_S3_KEY']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
SLACK_WEBHOOK_PARAMETER_NAME = os.environ['SLACK_WEBHOOK_PARAMETER_NAME']
AWS_REGION = os.environ['AWS_REGION']


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function
    
    Args:
        event: CloudTrail event from EventBridge
        context: Lambda context object
        
    Returns:
        Response dictionary with status and details
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract user identity from CloudTrail event
        user_info = extract_user_identity(event)
        event_time = event.get('detail', {}).get('eventTime', 'Unknown')
        event_name = event.get('detail', {}).get('eventName', 'Unknown')
        
        logger.info(f"Event: {event_name} by {user_info['user']} at {event_time}")
        
        # Load baseline rules from S3
        baseline_rules = load_baseline_from_s3()
        
        # Get current Security Group rules
        current_rules = get_current_sg_rules()
        
        # Compare and identify drift
        drift_detected = compare_rules(baseline_rules, current_rules)
        
        if not drift_detected['has_drift']:
            logger.info("No drift detected. All rules are compliant with baseline.")
            return {
                'statusCode': 200,
                'body': json.dumps('No drift detected')
            }
        
        # Remove unauthorized rules
        remediation_results = revoke_unauthorized_rules(drift_detected)
        
        # Send notifications
        send_notifications(
            user_info=user_info,
            event_time=event_time,
            event_name=event_name,
            drift_info=drift_detected,
            remediation_results=remediation_results
        )
        
        logger.info("Drift detection and remediation completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Drift detected and remediated',
                'unauthorized_rules_removed': len(remediation_results['revoked']),
                'details': remediation_results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        
        # Send error notification
        try:
            send_error_notification(str(e), event)
        except Exception as notify_error:
            logger.error(f"Failed to send error notification: {str(notify_error)}")
        
        raise


def load_baseline_from_s3() -> Dict[str, Any]:
    """
    Load baseline Security Group rules from S3
    
    Returns:
        Dictionary containing baseline rules (ingress and egress)
    """
    try:
        logger.info(f"Loading baseline from s3://{BASELINE_BUCKET}/{BASELINE_S3_KEY}")
        
        response = s3_client.get_object(
            Bucket=BASELINE_BUCKET,
            Key=BASELINE_S3_KEY
        )
        
        baseline_data = json.loads(response['Body'].read().decode('utf-8'))
        logger.info(f"Baseline loaded successfully for SG: {baseline_data.get('security_group_id')}")
        
        return baseline_data['baseline_rules']
        
    except ClientError as e:
        logger.error(f"Failed to load baseline from S3: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse baseline JSON: {str(e)}")
        raise


def get_current_sg_rules() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch current Security Group rules from AWS
    
    Returns:
        Dictionary with 'ingress' and 'egress' rule lists
    """
    try:
        logger.info(f"Fetching current rules for Security Group: {SECURITY_GROUP_ID}")
        
        response = ec2_client.describe_security_groups(
            GroupIds=[SECURITY_GROUP_ID]
        )
        
        if not response['SecurityGroups']:
            raise ValueError(f"Security Group {SECURITY_GROUP_ID} not found")
        
        sg = response['SecurityGroups'][0]
        
        current_rules = {
            'ingress': sg.get('IpPermissions', []),
            'egress': sg.get('IpPermissionsEgress', [])
        }
        
        logger.info(f"Found {len(current_rules['ingress'])} ingress and "
                   f"{len(current_rules['egress'])} egress rules")
        
        return current_rules
        
    except ClientError as e:
        logger.error(f"Failed to fetch Security Group rules: {str(e)}")
        raise


def compare_rules(baseline: Dict[str, List], current: Dict[str, List]) -> Dict[str, Any]:
    """
    Compare current rules against baseline and identify unauthorized rules
    
    Args:
        baseline: Baseline rules from S3
        current: Current rules from AWS
        
    Returns:
        Dictionary containing drift information and unauthorized rules
    """
    logger.info("Comparing current rules against baseline")
    
    unauthorized = {
        'ingress': [],
        'egress': []
    }
    
    # Compare ingress rules
    for rule in current['ingress']:
        if not is_rule_in_baseline(rule, baseline.get('ingress', [])):
            unauthorized['ingress'].append(rule)
            logger.warning(f"Unauthorized ingress rule detected: {format_rule_summary(rule)}")
    
    # Compare egress rules
    for rule in current['egress']:
        if not is_rule_in_baseline(rule, baseline.get('egress', [])):
            unauthorized['egress'].append(rule)
            logger.warning(f"Unauthorized egress rule detected: {format_rule_summary(rule)}")
    
    has_drift = len(unauthorized['ingress']) > 0 or len(unauthorized['egress']) > 0
    
    return {
        'has_drift': has_drift,
        'unauthorized_rules': unauthorized,
        'total_unauthorized': len(unauthorized['ingress']) + len(unauthorized['egress'])
    }


def is_rule_in_baseline(rule: Dict, baseline_rules: List[Dict]) -> bool:
    """
    Check if a rule exists in the baseline
    
    Args:
        rule: Rule to check
        baseline_rules: List of baseline rules
        
    Returns:
        True if rule is in baseline, False otherwise
    """
    # Normalize rule for comparison (remove metadata fields)
    normalized_rule = normalize_rule(rule)
    
    for baseline_rule in baseline_rules:
        normalized_baseline = normalize_rule(baseline_rule)
        if rules_match(normalized_rule, normalized_baseline):
            return True
    
    return False


def normalize_rule(rule: Dict) -> Dict:
    """
    Normalize rule for comparison by removing AWS-added metadata
    
    Args:
        rule: Security Group rule
        
    Returns:
        Normalized rule dictionary
    """
    # Keep only essential fields for comparison
    normalized = {
        'IpProtocol': rule.get('IpProtocol'),
        'FromPort': rule.get('FromPort'),
        'ToPort': rule.get('ToPort'),
        'IpRanges': sorted([r.get('CidrIp') for r in rule.get('IpRanges', [])]),
        'Ipv6Ranges': sorted([r.get('CidrIpv6') for r in rule.get('Ipv6Ranges', [])]),
        'PrefixListIds': sorted([p.get('PrefixListId') for p in rule.get('PrefixListIds', [])]),
        'UserIdGroupPairs': sorted([g.get('GroupId') for g in rule.get('UserIdGroupPairs', [])])
    }
    
    # Remove None and empty values
    normalized = {k: v for k, v in normalized.items() if v}
    
    return normalized


def rules_match(rule1: Dict, rule2: Dict) -> bool:
    """
    Check if two normalized rules match
    
    Args:
        rule1: First rule
        rule2: Second rule
        
    Returns:
        True if rules match, False otherwise
    """
    return rule1 == rule2


def revoke_unauthorized_rules(drift_info: Dict) -> Dict[str, Any]:
    """
    Revoke unauthorized ingress and egress rules
    
    Args:
        drift_info: Dictionary containing unauthorized rules
        
    Returns:
        Dictionary with remediation results
    """
    results = {
        'revoked': [],
        'failed': []
    }
    
    unauthorized = drift_info['unauthorized_rules']
    
    # Revoke unauthorized ingress rules
    for rule in unauthorized['ingress']:
        try:
            logger.info(f"Revoking unauthorized ingress rule: {format_rule_summary(rule)}")
            
            ec2_client.revoke_security_group_ingress(
                GroupId=SECURITY_GROUP_ID,
                IpPermissions=[rule]
            )
            
            results['revoked'].append({
                'type': 'ingress',
                'rule': format_rule_summary(rule)
            })
            
            logger.info(f"Successfully revoked ingress rule")
            
        except ClientError as e:
            logger.error(f"Failed to revoke ingress rule: {str(e)}")
            results['failed'].append({
                'type': 'ingress',
                'rule': format_rule_summary(rule),
                'error': str(e)
            })
    
    # Revoke unauthorized egress rules
    for rule in unauthorized['egress']:
        try:
            logger.info(f"Revoking unauthorized egress rule: {format_rule_summary(rule)}")
            
            ec2_client.revoke_security_group_egress(
                GroupId=SECURITY_GROUP_ID,
                IpPermissions=[rule]
            )
            
            results['revoked'].append({
                'type': 'egress',
                'rule': format_rule_summary(rule)
            })
            
            logger.info(f"Successfully revoked egress rule")
            
        except ClientError as e:
            logger.error(f"Failed to revoke egress rule: {str(e)}")
            results['failed'].append({
                'type': 'egress',
                'rule': format_rule_summary(rule),
                'error': str(e)
            })
    
    return results


def format_rule_summary(rule: Dict) -> str:
    """
    Format a rule into a human-readable summary
    
    Args:
        rule: Security Group rule
        
    Returns:
        Formatted string summary
    """
    protocol = rule.get('IpProtocol', 'all')
    from_port = rule.get('FromPort', 'all')
    to_port = rule.get('ToPort', 'all')
    
    cidrs = [r.get('CidrIp', '') for r in rule.get('IpRanges', [])]
    ipv6_cidrs = [r.get('CidrIpv6', '') for r in rule.get('Ipv6Ranges', [])]
    groups = [g.get('GroupId', '') for g in rule.get('UserIdGroupPairs', [])]
    
    sources = cidrs + ipv6_cidrs + groups
    sources_str = ', '.join(filter(None, sources)) or 'unknown'
    
    if protocol == '-1':
        return f"All traffic from {sources_str}"
    elif from_port == to_port:
        return f"Protocol {protocol}, Port {from_port} from {sources_str}"
    else:
        return f"Protocol {protocol}, Ports {from_port}-{to_port} from {sources_str}"


def extract_user_identity(event: Dict) -> Dict[str, str]:
    """
    Extract user identity information from CloudTrail event
    
    Args:
        event: CloudTrail event from EventBridge
        
    Returns:
        Dictionary with user identity details
    """
    detail = event.get('detail', {})
    user_identity = detail.get('userIdentity', {})
    
    user_type = user_identity.get('type', 'Unknown')
    principal_id = user_identity.get('principalId', 'Unknown')
    arn = user_identity.get('arn', 'Unknown')
    
    # Extract username or role name
    if user_type == 'IAMUser':
        user = user_identity.get('userName', 'Unknown')
    elif user_type == 'AssumedRole':
        user = user_identity.get('sessionContext', {}).get('sessionIssuer', {}).get('userName', 'Unknown')
    else:
        user = principal_id
    
    return {
        'user': user,
        'type': user_type,
        'arn': arn,
        'principal_id': principal_id
    }


def send_notifications(user_info: Dict, event_time: str, event_name: str,
                      drift_info: Dict, remediation_results: Dict) -> None:
    """
    Send notifications to SNS (email) and Slack
    
    Args:
        user_info: User identity information
        event_time: Event timestamp
        event_name: CloudTrail event name
        drift_info: Drift detection results
        remediation_results: Remediation results
    """
    # Create notification message
    message = format_notification_message(
        user_info, event_time, event_name, drift_info, remediation_results
    )
    
    # Send to SNS (email)
    try:
        logger.info("Sending notification to SNS")
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"🚨 Security Group Drift Detected - {SECURITY_GROUP_ID}",
            Message=message
        )
        logger.info("SNS notification sent successfully")
    except ClientError as e:
        logger.error(f"Failed to send SNS notification: {str(e)}")
    
    # Send to Slack
    try:
        send_slack_notification(user_info, event_time, drift_info, remediation_results)
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {str(e)}")


def format_notification_message(user_info: Dict, event_time: str, event_name: str,
                                drift_info: Dict, remediation_results: Dict) -> str:
    """
    Format notification message for SNS/email
    
    Returns:
        Formatted message string
    """
    message = f"""
🚨 SECURITY GROUP DRIFT DETECTED AND REMEDIATED 🚨

Security Group: {SECURITY_GROUP_ID}
Region: {AWS_REGION}
Event: {event_name}
Timestamp: {event_time}

👤 CHANGE MADE BY:
User: {user_info['user']}
Type: {user_info['type']}
ARN: {user_info['arn']}

📊 DRIFT SUMMARY:
Total Unauthorized Rules: {drift_info['total_unauthorized']}
Unauthorized Ingress Rules: {len(drift_info['unauthorized_rules']['ingress'])}
Unauthorized Egress Rules: {len(drift_info['unauthorized_rules']['egress'])}

✅ REMEDIATION RESULTS:
Rules Revoked: {len(remediation_results['revoked'])}
Failed Revocations: {len(remediation_results['failed'])}

🔍 REVOKED RULES:
"""
    
    for item in remediation_results['revoked']:
        message += f"\n  - [{item['type'].upper()}] {item['rule']}"
    
    if remediation_results['failed']:
        message += "\n\n❌ FAILED TO REVOKE:\n"
        for item in remediation_results['failed']:
            message += f"\n  - [{item['type'].upper()}] {item['rule']}\n    Error: {item['error']}"
    
    message += f"\n\n🔗 CloudWatch Logs: https://{AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region={AWS_REGION}#logsV2:log-groups"
    message += f"\n🔗 Security Group: https://{AWS_REGION}.console.aws.amazon.com/ec2/home?region={AWS_REGION}#SecurityGroup:groupId={SECURITY_GROUP_ID}"
    
    return message


def send_slack_notification(user_info: Dict, event_time: str,
                           drift_info: Dict, remediation_results: Dict) -> None:
    """
    Send formatted notification to Slack webhook
    
    Args:
        user_info: User identity information
        event_time: Event timestamp
        drift_info: Drift detection results
        remediation_results: Remediation results
    """
    try:
        # Get Slack webhook URL from SSM Parameter Store
        logger.info(f"Retrieving Slack webhook from SSM: {SLACK_WEBHOOK_PARAMETER_NAME}")
        
        response = ssm_client.get_parameter(
            Name=SLACK_WEBHOOK_PARAMETER_NAME,
            WithDecryption=True
        )
        
        webhook_url = response['Parameter']['Value']
        
        # Skip if placeholder value
        if 'REPLACE_WITH_YOUR_WEBHOOK_URL' in webhook_url:
            logger.warning("Slack webhook URL is still placeholder - skipping Slack notification")
            return
        
        # Format Slack message
        slack_message = {
            "text": f"🚨 Security Group Drift Detected: {SECURITY_GROUP_ID}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Security Group Drift Detected & Remediated"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Security Group:*\n{SECURITY_GROUP_ID}"},
                        {"type": "mrkdwn", "text": f"*Region:*\n{AWS_REGION}"},
                        {"type": "mrkdwn", "text": f"*Changed By:*\n{user_info['user']}"},
                        {"type": "mrkdwn", "text": f"*Timestamp:*\n{event_time}"}
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Unauthorized Rules:*\n{drift_info['total_unauthorized']}"},
                        {"type": "mrkdwn", "text": f"*Rules Revoked:*\n{len(remediation_results['revoked'])}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Revoked Rules:*\n" + "\n".join([
                            f"• [{r['type'].upper()}] {r['rule']}"
                            for r in remediation_results['revoked']
                        ])
                    }
                }
            ]
        }
        
        # Send to Slack
        logger.info("Sending notification to Slack")
        encoded_data = json.dumps(slack_message).encode('utf-8')
        
        response = http.request(
            'POST',
            webhook_url,
            body=encoded_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status == 200:
            logger.info("Slack notification sent successfully")
        else:
            logger.error(f"Slack notification failed with status {response.status}: {response.data}")
            
    except ClientError as e:
        logger.error(f"Failed to retrieve Slack webhook from SSM: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {str(e)}")
        raise


def send_error_notification(error_message: str, event: Dict) -> None:
    """
    Send error notification when Lambda fails
    
    Args:
        error_message: Error message
        event: Original event that caused the error
    """
    message = f"""
❌ ERROR IN DRIFT DETECTOR LAMBDA

Security Group: {SECURITY_GROUP_ID}
Region: {AWS_REGION}
Timestamp: {datetime.utcnow().isoformat()}

Error: {error_message}

Event Details:
{json.dumps(event, indent=2, default=str)}

Please check CloudWatch Logs for more details.
"""
    
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"❌ Drift Detector Error - {SECURITY_GROUP_ID}",
            Message=message
        )
    except Exception as e:
        logger.error(f"Failed to send error notification: {str(e)}")
