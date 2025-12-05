# Security Group Drift Detector - Improvement Plan

This document outlines the **Should Fix** and **Nice to Have** improvements for the drift detection system, including importance, current gaps, and step-by-step implementation plans.

---

## 📊 SHOULD FIX ITEMS (Medium Priority)

These items address operational reliability and completeness issues that could cause problems in production.

---

### 1. Add Idempotency/Deduplication Protection

**Priority**: HIGH
**Estimated Effort**: 2-3 hours
**AWS Cost Impact**: ~$0.50/month (CloudWatch Logs only)

#### **Importance**
- **Problem**: EventBridge may retry Lambda invocations on transient failures
- **Impact**:
  - Duplicate notifications sent to email/Slack
  - Attempting to revoke already-revoked rules (causes errors)
  - Confusing audit trail in CloudWatch Logs
  - User receives multiple alerts for the same drift event

#### **Current Gap**
The Lambda function has no mechanism to detect if it has already processed a specific CloudTrail event. Each invocation is treated as unique.

#### **Solution Plan**

**Approach**: Use CloudWatch Logs Insights for deduplication (no additional AWS services needed)

**Step-by-Step Implementation**:

1. **Add Event ID Extraction** (5 min)
   - Extract `eventID` from CloudTrail event (unique identifier)
   - Extract `eventTime` for correlation

2. **Add Deduplication Check** (15 min)
   - At start of `lambda_handler()`, check if event was already processed
   - Use structured logging with event ID
   - Query recent CloudWatch Logs for duplicate event ID

3. **Add Structured Logging** (20 min)
   - Log event ID in JSON format for easy querying
   - Add processing status markers

4. **Add Early Exit Logic** (10 min)
   - If duplicate detected, log warning and exit gracefully
   - Return success (don't trigger retry)

5. **Testing** (30 min)
   - Manually invoke Lambda twice with same event
   - Verify second invocation is skipped
   - Verify only one notification sent

**Code Changes Required**:
- `lambda/drift_detector.py`: Add deduplication logic in `lambda_handler()`
- Add helper function `is_duplicate_event(event_id)`

**Alternative (if simple approach insufficient)**:
- Use DynamoDB table to track processed events (adds ~$0.25/month)
- TTL set to 24 hours to auto-cleanup old records

---

### 2. Monitor RevokeSecurityGroup Events

**Priority**: HIGH
**Estimated Effort**: 1 hour
**AWS Cost Impact**: $0 (uses existing EventBridge rule)

#### **Importance**
- **Problem**: System only monitors rule **additions**, not **deletions**
- **Impact**:
  - If someone removes a baseline rule, system doesn't detect it
  - Security posture weakens without notification
  - Baseline drift goes unnoticed

#### **Current Gap**
EventBridge rule only captures:
- `AuthorizeSecurityGroupIngress`
- `AuthorizeSecurityGroupEgress`

Missing:
- `RevokeSecurityGroupIngress`
- `RevokeSecurityGroupEgress`
- `ModifySecurityGroupRules` (newer unified API)

#### **Solution Plan**

**Step-by-Step Implementation**:

1. **Update EventBridge Pattern** (10 min)
   - Edit `terraform/modules/eventbridge/main.tf`
   - Add `RevokeSecurityGroupIngress` and `RevokeSecurityGroupEgress` to event pattern
   - Add `ModifySecurityGroupRules` for comprehensive coverage

2. **Update Lambda Logic** (30 min)
   - Modify `lambda_handler()` to detect event type
   - For Revoke events: Check if removed rule was in baseline
   - If baseline rule removed: Re-add it automatically
   - Send notification about unauthorized removal

3. **Add Re-Authorization Logic** (15 min)
   - Create new function `restore_baseline_rules()`
   - Use `authorize_security_group_ingress/egress` to restore rules
   - Handle edge cases (rule already exists)

4. **Update Notifications** (5 min)
   - Modify notification message to distinguish between:
     - "Unauthorized rule added (and removed)"
     - "Baseline rule removed (and restored)"

**Code Changes Required**:
- `terraform/modules/eventbridge/main.tf`: Update event pattern
- `lambda/drift_detector.py`: Add revoke detection and restoration logic

---

### 3. Add Baseline Versioning in S3

**Priority**: MEDIUM
**Estimated Effort**: 1.5 hours
**AWS Cost Impact**: ~$0.10/month (S3 storage for versions)

#### **Importance**
- **Problem**: No history of baseline changes
- **Impact**:
  - Can't rollback to previous baseline if mistake made
  - No audit trail of who changed baseline and when
  - Difficult to troubleshoot drift detection issues

#### **Current Gap**
Baseline is stored as single file: `baseline/security-group-baseline.json`
- Overwrites on each update
- No version history
- No metadata about who/when updated

#### **Solution Plan**

**Approach**: Use S3 versioning + timestamped copies

**Step-by-Step Implementation**:

1. **Enable S3 Versioning** (5 min)
   - Update `terraform/modules/storage/main.tf`
   - Add `versioning` block to S3 bucket resource

2. **Update Export Script** (30 min)
   - Modify `scripts/export_baseline.py`
   - Create timestamped copy: `baseline/history/baseline-YYYY-MM-DD-HHmmss.json`
   - Keep main file at `baseline/security-group-baseline.json` (for Lambda)
   - Add version metadata to JSON

3. **Add Rollback Script** (45 min)
   - Create `scripts/rollback_baseline.py`
   - List available baseline versions
   - Allow user to select version to restore
   - Copy selected version to main baseline path

4. **Add Baseline Comparison Tool** (10 min)
   - Create `scripts/compare_baselines.py`
   - Show diff between two baseline versions
   - Highlight added/removed rules

**Code Changes Required**:
- `terraform/modules/storage/main.tf`: Enable versioning
- `scripts/export_baseline.py`: Add timestamped copies
- `scripts/rollback_baseline.py`: New file
- `scripts/compare_baselines.py`: New file

---

### 4. Add CloudTrail Health Check

**Priority**: MEDIUM
**Estimated Effort**: 1 hour
**AWS Cost Impact**: $0 (uses existing CloudWatch)

#### **Importance**
- **Problem**: System assumes CloudTrail is working
- **Impact**:
  - If CloudTrail disabled/misconfigured, system is blind
  - No alerts when drift detection stops working
  - False sense of security

#### **Current Gap**
No monitoring of:
- CloudTrail trail status (enabled/disabled)
- EventBridge rule status
- Lambda invocation frequency

#### **Solution Plan**

**Approach**: Add CloudWatch Alarm for Lambda invocation anomalies

**Step-by-Step Implementation**:

1. **Add CloudWatch Alarm** (20 min)
   - Create alarm in `terraform/modules/lambda/main.tf`
   - Monitor Lambda invocation count
   - Alert if no invocations in 7 days (suggests CloudTrail issue)

2. **Add Health Check Lambda** (30 min)
   - Create separate Lambda function
   - Runs daily via EventBridge schedule
   - Checks:
     - CloudTrail trail status
     - EventBridge rule enabled
     - Recent Lambda invocations
   - Sends alert if issues detected

3. **Add to Terraform** (10 min)
   - Create new module `terraform/modules/monitoring`
   - Deploy health check Lambda
   - Configure daily schedule

**Code Changes Required**:
- `terraform/modules/monitoring/`: New module
- `lambda/health_check.py`: New file
- `terraform/main.tf`: Include monitoring module

---





---

## 🎯 NICE TO HAVE ITEMS (Enhancement Features)

These items improve observability, testing, and operational excellence but are not critical for core functionality.

---

### 5. Add Dead Letter Queue (DLQ) for Failed Invocations

**Priority**: LOW
**Estimated Effort**: 30 minutes
**AWS Cost Impact**: ~$0.10/month (SQS + minimal storage)

#### **Importance**
- **Problem**: Failed Lambda invocations are lost after retry exhaustion
- **Impact**:
  - No visibility into persistent failures
  - Drift events may be missed
  - Difficult to debug recurring issues

#### **Current Gap**
Lambda has no DLQ configured. If invocation fails 3 times (EventBridge default), event is discarded.

#### **Solution Plan**

**Step-by-Step Implementation**:

1. **Create SQS DLQ** (10 min)
   - Add to `terraform/modules/lambda/main.tf`
   - Create SQS queue with 14-day retention
   - Configure encryption

2. **Attach DLQ to Lambda** (5 min)
   - Add `dead_letter_config` to Lambda resource
   - Point to SQS queue ARN

3. **Add DLQ Alarm** (10 min)
   - Create CloudWatch Alarm
   - Alert when messages appear in DLQ
   - Send to SNS topic (reuse existing)

4. **Add DLQ Processing Script** (5 min)
   - Create `scripts/process_dlq.py`
   - Read messages from DLQ
   - Allow manual retry or analysis

**Code Changes Required**:
- `terraform/modules/lambda/main.tf`: Add SQS queue and DLQ config
- `scripts/process_dlq.py`: New file

**Benefits**:
- Never lose drift events
- Easy debugging of failures
- Metrics on failure rate

---

### 6. Add CloudWatch Dashboard

**Priority**: LOW
**Estimated Effort**: 1 hour
**AWS Cost Impact**: $3/month (CloudWatch Dashboard)

#### **Importance**
- **Problem**: No centralized view of system health
- **Impact**:
  - Must check multiple places for status
  - No historical trends
  - Difficult to demonstrate value to stakeholders

#### **Current Gap**
Metrics scattered across:
- CloudWatch Logs (Lambda execution)
- SNS (notification delivery)
- EventBridge (rule matches)

#### **Solution Plan**

**Step-by-Step Implementation**:

1. **Create Dashboard Resource** (20 min)
   - Add to `terraform/modules/monitoring/main.tf`
   - Define dashboard JSON structure

2. **Add Key Metrics Widgets** (30 min)
   - Lambda invocation count (line graph)
   - Drift events detected (counter)
   - Rules remediated (counter)
   - Lambda errors (line graph)
   - Lambda duration (line graph)
   - SNS notification delivery rate

3. **Add Log Insights Queries** (10 min)
   - Top users triggering drift
   - Most common unauthorized rules
   - Remediation success rate

**Code Changes Required**:
- `terraform/modules/monitoring/dashboard.tf`: New file
- Dashboard JSON configuration

**Benefits**:
- At-a-glance system health
- Historical trends
- Executive reporting

---

### 7. Add Automated Testing

**Priority**: LOW
**Estimated Effort**: 2-3 hours
**AWS Cost Impact**: $0 (local testing)

#### **Importance**
- **Problem**: No automated tests for Lambda function
- **Impact**:
  - Changes may introduce bugs
  - Difficult to refactor safely
  - No confidence in deployments

#### **Current Gap**
`lambda/tests/` directory exists but is empty.

#### **Solution Plan**

**Step-by-Step Implementation**:

1. **Set Up Test Framework** (15 min)
   - Create `lambda/tests/test_drift_detector.py`
   - Use `pytest` and `moto` (AWS mocking)
   - Add to `lambda/requirements-dev.txt`

2. **Write Unit Tests** (90 min)
   - Test `normalize_rule()` function
   - Test `compare_rules()` logic
   - Test `extract_user_identity()` parsing
   - Test `format_notification_message()`
   - Mock AWS API calls

3. **Write Integration Tests** (45 min)
   - Test full `lambda_handler()` flow
   - Mock S3, EC2, SNS, SSM
   - Verify rule revocation logic
   - Verify notification sending

4. **Add CI/CD Integration** (30 min)
   - Create `.github/workflows/test.yml`
   - Run tests on every commit
   - Require passing tests before merge

**Code Changes Required**:
- `lambda/tests/test_drift_detector.py`: New file
- `lambda/requirements-dev.txt`: New file
- `.github/workflows/test.yml`: New file

**Benefits**:
- Catch bugs before deployment
- Safe refactoring
- Documentation via tests

---

### 8. Add Metrics and Custom CloudWatch Metrics

**Priority**: LOW
**Estimated Effort**: 1 hour
**AWS Cost Impact**: ~$0.30/month (custom metrics)

#### **Importance**
- **Problem**: Limited visibility into drift patterns
- **Impact**:
  - Can't identify repeat offenders
  - Can't measure system effectiveness
  - No data for security reports

#### **Current Gap**
Only default Lambda metrics available. No custom business metrics.

#### **Solution Plan**

**Step-by-Step Implementation**:

1. **Add CloudWatch Metrics Client** (10 min)
   - Import `cloudwatch` client in Lambda
   - Add IAM permission for `PutMetricData`

2. **Publish Custom Metrics** (30 min)
   - `DriftEventsDetected` (count)
   - `UnauthorizedRulesRevoked` (count)
   - `BaselineComplianceRate` (percentage)
   - `RemediationLatency` (milliseconds)
   - Dimension by Security Group ID

3. **Create Metric Alarms** (15 min)
   - Alert on high drift rate (>10/day)
   - Alert on low compliance rate (<95%)
   - Alert on high remediation latency (>5 seconds)

4. **Add to Dashboard** (5 min)
   - Include custom metrics in CloudWatch Dashboard
   - Create trend graphs

**Code Changes Required**:
- `lambda/drift_detector.py`: Add metric publishing
- `terraform/modules/lambda/iam.tf`: Add CloudWatch permissions
- `terraform/modules/monitoring/alarms.tf`: New file

**Benefits**:
- Quantify security posture
- Identify trends
- Proactive alerting

---

## 📋 Implementation Priority Recommendation

Based on **impact vs. effort**, here's the recommended order:

### **Phase 1: Critical Reliability** (Week 1)
1. ✅ Add Idempotency/Deduplication Protection
2. ✅ Monitor RevokeSecurityGroup Events
3. ✅ Add Dead Letter Queue

### **Phase 2: Operational Excellence** (Week 2)
4. ✅ Add Baseline Versioning
5. ✅ Add CloudTrail Health Check
6. ✅ Add Custom Metrics

### **Phase 3: Observability** (Week 3)
7. ✅ Add CloudWatch Dashboard
8. ✅ Add Automated Testing

### **Phase 4: Advanced Features** (Future)
9. ⏸️ Add Multi-Region Support (if needed)
10. ⏸️ Add Slack Interactive Buttons (if needed)

---

## 💰 Total Cost Estimate

| Item | Monthly Cost |
|------|--------------|
| Current System | ~$0.05 |
| + Idempotency (CloudWatch Logs) | +$0.50 |
| + Baseline Versioning (S3) | +$0.10 |
| + DLQ (SQS) | +$0.10 |
| + Custom Metrics | +$0.30 |
| + CloudWatch Dashboard | +$3.00 |
| **Total (All Improvements)** | **~$4.05/month** |

**Note**: Multi-region support would multiply costs by number of regions.

---

## 🎯 Quick Wins (< 1 hour each)

If you want immediate improvements with minimal effort:

1. **Add DLQ** (30 min) - Never lose events
2. **Monitor Revoke Events** (1 hour) - Complete coverage
3. **Enable S3 Versioning** (5 min) - Baseline history

---

## ❓ Questions Before Implementation

1. **Which phase do you want to start with?**
2. **Is the $4/month cost acceptable for all improvements?**
3. **Do you need multi-region support?**
4. **Should I implement any of these now, or just keep as a plan?**
