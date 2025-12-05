# Security Group Drift Detector - Fixes Applied

## ✅ MUST FIX Issues - COMPLETED

All critical issues have been resolved. The system is now ready for deployment.

---

### 1. ✅ Lambda Packaging with Dependencies

**Problem**: Lambda deployment package only included `.py` file, missing dependencies from `requirements.txt`.

**Solution Applied**:
- Created `scripts/build_lambda.sh` - automated build script
- Installs dependencies using `pip install -r requirements.txt`
- Packages everything into deployment-ready zip file
- Removes unnecessary files to minimize package size
- Updated Terraform to use pre-built package

**Files Changed**:
- ✅ `scripts/build_lambda.sh` - NEW (build script)
- ✅ `terraform/modules/lambda/main.tf` - Updated packaging logic
- ✅ `README.md` - Added build instructions

**How to Use**:
```bash
# Run before terraform apply
./scripts/build_lambda.sh
```

---

### 2. ✅ Deprecated boto3 API Fixed

**Problem**: `scripts/export_baseline.py` used deprecated internal boto3 APIs that will break in future versions.

**Solution Applied**:
- Replaced `boto3.utils.datetime2timestamp()` with standard `datetime.utcnow().isoformat()`
- Removed dependency on `boto3.compat.datetime`
- Uses Python standard library instead

**Files Changed**:
- ✅ `scripts/export_baseline.py` - Fixed datetime handling

**Before**:
```python
'created_at': boto3.utils.datetime2timestamp(
    boto3.compat.datetime.datetime.utcnow()
)
```

**After**:
```python
'created_at': datetime.utcnow().isoformat() + 'Z'
```

---

### 3. ✅ SSM Parameter Error Handling

**Problem**: Lambda would crash if Slack webhook SSM parameter was missing or inaccessible.

**Solution Applied**:
- Added graceful error handling for SSM parameter retrieval
- Detects `ParameterNotFound` and `AccessDeniedException` errors
- Logs warning and continues without Slack notification
- Validates webhook URL format before sending
- System continues to work with email-only notifications

**Files Changed**:
- ✅ `lambda/drift_detector.py` - Enhanced error handling
- ✅ `README.md` - Added Slack webhook setup instructions

**Behavior**:
- If SSM parameter missing → Logs warning, skips Slack, sends email
- If webhook is placeholder → Skips Slack notification
- If Slack fails → Logs error, continues with email
- **Lambda never fails due to Slack issues**

---

## 📋 Next Steps

### Before Deployment

1. **Build Lambda Package**:
   ```bash
   ./scripts/build_lambda.sh
   ```

2. **Configure Terraform Variables**:
   - Edit `terraform/terraform.tfvars`
   - Set your Security Group ID, email, etc.

3. **Deploy Infrastructure**:
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

4. **Confirm Email Subscription**:
   - Check inbox for SNS confirmation
   - Click confirmation link

5. **Update Slack Webhook** (Optional):
   ```bash
   aws ssm put-parameter \
     --name "/sg-drift-detector/prod/slack-webhook-url" \
     --value "https://hooks.slack.com/services/YOUR/WEBHOOK" \
     --type "SecureString" \
     --overwrite
   ```

6. **Export Baseline**:
   ```bash
   cd scripts
   python3 export_baseline.py
   ```

7. **Test the System**:
   - Manually add unauthorized rule to Security Group
   - Verify auto-remediation within 30 seconds
   - Check email and Slack for notifications

---

## 📖 Additional Documentation

- **`IMPROVEMENT_PLAN.md`** - Detailed plan for "Should Fix" and "Nice to Have" improvements
  - 8 additional enhancements documented
  - Step-by-step implementation guides
  - Cost estimates and priority recommendations
  - Quick wins identified

---

## 🎯 System Status

| Component | Status | Notes |
|-----------|--------|-------|
| Lambda Packaging | ✅ Fixed | Build script created |
| Dependencies | ✅ Fixed | Automated installation |
| boto3 APIs | ✅ Fixed | Using standard library |
| Error Handling | ✅ Fixed | Graceful SSM failures |
| Slack Integration | ✅ Enhanced | Optional with fallback |
| Documentation | ✅ Updated | Build + setup instructions |

**The system is production-ready!** 🚀

---

## 💡 Recommendations

1. **Deploy to staging first** - Test with non-critical Security Group
2. **Monitor CloudWatch Logs** - Watch first few drift events
3. **Review IMPROVEMENT_PLAN.md** - Consider Phase 1 improvements
4. **Set up CloudTrail** - Ensure it's enabled and logging API events

---

## 🆘 Troubleshooting

### Build Script Fails
```bash
# Ensure pip3 is installed
pip3 --version

# Install dependencies manually
pip3 install -r lambda/requirements.txt -t build/lambda
```

### Lambda Can't Find Dependencies
- Verify `build_lambda.sh` ran successfully
- Check `terraform/modules/lambda/lambda_function.zip` exists
- Verify zip contains both `.py` file and dependency folders

### Slack Notifications Not Working
- Check SSM parameter exists and has correct webhook URL
- Verify Lambda has permission to read SSM parameter
- Check CloudWatch Logs for Slack-related errors
- System will still work with email-only notifications

---

**All critical fixes applied successfully!** ✅

