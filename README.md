# Google Workspace to AWS SSO Group Sync
##💡 Why This Solution Exists

While AWS Identity Center (SSO) integrates with Google Workspace for user authentication, there’s a gap when it comes to automatic group and membership synchronization.

##  The Challenge:
    AWS SSO’s built-in Google Workspace integration only handles sign-in. Group memberships — which control fine-grained access in AWS — do not automatically stay in sync.
    This means every time a user changes teams, leaves the organization, or is added to a new Google group, manual updates are needed inside AWS SSO. In large organizations or multi-account AWS setups, this quickly becomes a major operational burden and a source of access drift.

##  Why It Matters:
    Without automated sync, stale permissions can persist, users may retain access they shouldn’t, and onboarding/offboarding processes become slower and riskier.

##  The Solution:
    This serverless automation continuously syncs Google Workspace groups, users, and memberships into AWS SSO — ensuring your AWS access mirrors your Google Workspace organization structure without manual intervention.

## 🎯 Overview

This serverless solution automatically synchronizes Google Workspace groups and users with AWS SSO (Identity Center), ensuring your AWS access permissions stay in sync with your Google Workspace organization structure.

## 🚧 Limitations of Native Google Workspace ↔ AWS SSO Integration

AWS’s native Google Workspace integration:

    ✔ Provides single sign-on (SSO) login.

    ❌ Does not sync group memberships into AWS.

    ❌ Requires manual group management in AWS SSO.

    ❌ Lacks automated cleanup of removed users or changed memberships.

    ❌ No built-in scheduling for ongoing synchronization.

This custom solution:

    🔄 Runs automatically every 15–30 minutes via EventBridge.

    📥 Pulls group and membership data from Google Workspace.

    📤 Updates AWS SSO groups and users accordingly.

    🧹 Optionally removes extra AWS SSO members who are no longer in the Google group.

    📊 Provides full logging and monitoring through CloudWatch.

## 🏗️ Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   🏢 Google         │    │   🔧 AWS Lambda      │    │   🔐 AWS SSO        │
│   Workspace         │───►│   Sync Function      │───►│   Identity Center   │
│                     │    │                      │    │                     │
│   👥 Groups         │    │   🐍 Python 3.9      │    │   👤 Users          │
│   👤 Users          │    │   📡 Google APIs     │    │   👥 Groups         │
│   🔗 Memberships    │    │   ☁️  AWS SDK        │    │   🔗 Memberships    │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
         │                           │                           │
         │                  ┌────────▼────────┐                 │
         │                  │   🔒 AWS        │                 │
         │                  │   Secrets       │                 │
         │                  │   Manager       │                 │
         │                  │                 │                 │
         │                  │ 🔑 Service      │                 │
         │                  │ Account Creds   │                 │
         │                  └─────────────────┘                 │
         │                           │                           │
         │                  ┌────────▼────────┐                 │
         │                  │   ⏰ EventBridge │                 │
         │                  │   Scheduler     │                 │
         │                  │                 │                 │
         │                  │ 🔄 Automated    │                 │
         │                  │ Sync (15-30min) │                 │
         │                  └─────────────────┘                 │
         │                                                       │
         └───────────────────────────────────────────────────────┘
                          ➡️ Unidirectional Sync
                     (Google Workspace → AWS SSO)
```

## ✨ Features

- **🔄 Automated Sync**: Scheduled synchronization every 15-30 minutes
- **👥 Group Management**: Syncs Google Workspace groups to AWS SSO groups
- **👤 User Management**: Syncs users and group memberships
- **🎯 Selective Sync**: Include/exclude specific groups
- **🧹 Cleanup**: Optional removal of extra members not in Google groups
- **📊 Monitoring**: CloudWatch logs and metrics
- **🔐 Secure**: Service account credentials stored in AWS Secrets Manager
- **⚡ Serverless**: No infrastructure to manage

## 🎁 Advantages

### Cost Effective
- **Serverless**: Pay only for execution time
- **No Infrastructure**: No EC2 instances or containers to manage
- **Minimal Resources**: Lambda function runs only when needed

### Security
- **IAM Roles**: Least privilege access using AWS IAM
- **Encrypted Storage**: Service account credentials encrypted in Secrets Manager
- **VPC Optional**: Can run in VPC for additional network security
- **Audit Trail**: All actions logged in CloudWatch

### Reliability
- **Event-Driven**: Reliable EventBridge scheduling
- **Error Handling**: Comprehensive error handling and retries
- **Monitoring**: Built-in CloudWatch monitoring and alerting
- **Scalable**: Automatically scales with your organization size

### Maintenance
- **Automated**: Set it and forget it operation
- **Updates**: Easy updates via CloudFormation
- **Flexible**: Configurable sync schedules and filters

## 📋 Prerequisites

### AWS Requirements
- **AWS CLI**: Configured with appropriate permissions
- **AWS SSO**: Identity Center enabled in your AWS account
- **Deployment Account**: 
  - ⚠️ **Important**: Deploy Lambda in the **IAM Identity Center delegated administration account**
  - ❌ **Not Recommended**: Deploying in management account (technically possible but not recommended)
  - 🔑 **CLI Credentials**: Must use credentials from IAM Identity Center delegated admin account
- **Permissions**: CloudFormation, Lambda, IAM, Secrets Manager, EventBridge access

### Google Workspace Requirements
- **Admin Access**: Google Workspace admin account
- **Service Account**: Google Cloud service account with domain-wide delegation
- **API Access**: Google Admin SDK and Directory API enabled
- **📚 Prerequisites Setup**: Use this workshop to complete the above Google Workspace requirements:
  [Google Workspace Integration with AWS Control Tower](https://catalog.workshops.aws/control-tower/en-US/authentication-authorization/google-workspace)
  
  ℹ️ *This workshop covers the same SSO sync setup and will guide you through creating the service account, enabling APIs, and configuring domain-wide delegation needed for this solution.*

### Local Environment
- **Python 3.7+**: For running deployment scripts
- **Bash**: Unix-like environment (Linux, macOS, WSL)
- **Internet Access**: For downloading dependencies

## 🚀 Quick Start

### 1. Google Workspace Setup

1. **Create Service Account**:
   ```bash
   # Go to Google Cloud Console
   # Create new service account
   # Download JSON key file
   ```

2. **Enable APIs**:
   - Admin SDK API
   - Directory API

3. **Domain-wide Delegation**:
   - Enable domain-wide delegation for service account
   - Add required scopes in Google Workspace Admin Console

### 2. AWS Setup

1. **Enable AWS SSO**:
   ```bash
   # Enable Identity Center in AWS Console
   # Note down Identity Store ID
   ```

2. **Configure AWS CLI**:
   ```bash
   aws configure
   # Enter your AWS credentials and region
   ```

### 3. Deploy Solution

1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd serverless
   ```

2. **Deploy**:
   ```bash
   ./deploy.sh \
     --stack-name gsuite-sso-sync \
     --identity-store-id d-1234567890 \
     --region us-east-1 \
     --schedule "rate(30 minutes)" \
     --domain company.com \
     --admin-email admin@company.com \
     --service-account /path/to/service-account.json \
     --log-retention 7
   ```

## ⚙️ Configuration Options

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `--stack-name` | CloudFormation stack name | `gsuite-aws-sso-sync` | No |
| `--region` | AWS region | From AWS CLI config | No |
| `--identity-store-id` | AWS SSO Identity Store ID | - | Yes |
| `--domain` | Google Workspace domain | - | Yes |
| `--admin-email` | Google Workspace admin email | - | Yes |
| `--service-account` | Path to service account JSON | - | Yes |
| `--schedule` | Sync schedule expression | `rate(15 minutes)` | No |
| `--include-groups` | Comma-separated groups to include | All groups | No |
| `--exclude-groups` | Comma-separated groups to exclude | None | No |
| `--remove-extra-members` | Remove extra members from AWS SSO | `false` | No |
| `--log-retention` | CloudWatch log retention days | `30` | No |

## 📊 Monitoring

### CloudWatch Logs
```bash
# View logs
aws logs tail /aws/lambda/gsuite-sso-sync-sync-function --follow

# Search logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/gsuite-sso-sync-sync-function \
  --filter-pattern "ERROR"
```

### Manual Execution
```bash
# Test the function
aws lambda invoke \
  --function-name gsuite-sso-sync-sync-function \
  --payload '{}' \
  response.json

# Check results
cat response.json
```

## 🔧 Troubleshooting

### Common Issues

1. **Permission Errors**:
   - Verify AWS IAM permissions
   - Check Google Workspace admin access
   - Ensure service account has domain-wide delegation

2. **Sync Failures**:
   - Check CloudWatch logs
   - Verify Google API quotas
   - Confirm Identity Store ID is correct

3. **Deployment Issues**:
   - Ensure AWS CLI is configured
   - Check CloudFormation stack events
   - Verify all required parameters

### Debug Commands
```bash
# Check stack status
aws cloudformation describe-stacks --stack-name gsuite-sso-sync

# View stack events
aws cloudformation describe-stack-events --stack-name gsuite-sso-sync

# Test Lambda function
aws lambda invoke \
  --function-name gsuite-sso-sync-sync-function \
  --log-type Tail \
  response.json
```

## 🔄 Updates

To update the solution:

```bash
# Redeploy with same parameters
./deploy.sh [same-parameters-as-initial-deployment]

# Or update specific components
aws lambda update-function-code \
  --function-name gsuite-sso-sync-sync-function \
  --zip-file fileb://function.zip
```

## 🗑️ Cleanup

To remove the solution:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name gsuite-sso-sync

# Clean up S3 bucket (if needed)
aws s3 rm s3://gsuite-sso-sync-deploy-ACCOUNT-REGION --recursive
aws s3 rb s3://gsuite-sso-sync-deploy-ACCOUNT-REGION
```

## 📞 Support

For issues and questions:
1. Check CloudWatch logs first
2. Review troubleshooting section
3. Verify prerequisites are met
4. Test with manual Lambda invocation

## 🔒 Security Best Practices

- **Rotate Service Account Keys**: Regularly rotate Google service account keys
- **Monitor Access**: Review CloudWatch logs regularly
- **Least Privilege**: Use minimal required permissions
- **Network Security**: Consider VPC deployment for sensitive environments
- **Backup**: Keep backup of service account credentials securely
