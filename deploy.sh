#!/bin/bash

# Enhanced Google Workspace to AWS SSO Group Sync - Deployment Script with Fixes

set -e

# Default values
STACK_NAME="gsuite-aws-sso-sync"
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
BUCKET_PREFIX="gsuite-sync-deploy"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -s, --stack-name NAME        CloudFormation stack name (default: gsuite-aws-sso-sync)"
    echo "  -r, --region REGION          AWS region (default: from AWS CLI config or us-east-1)"
    echo "  -i, --identity-store-id ID   AWS SSO Identity Store ID (required)"
    echo "  -d, --domain DOMAIN          Primary Google Workspace domain (required)"
    echo "  -e, --admin-email EMAIL      Google Workspace admin email (required)"
    echo "  -k, --service-account FILE   Path to Google service account JSON file (required)"
    echo "  --schedule EXPRESSION        Sync schedule (default: rate(15 minutes))"
    echo "  --include-groups GROUPS      Comma-separated list of groups to include"
    echo "  --exclude-groups GROUPS      Comma-separated list of groups to exclude"
    echo "  --remove-extra-members       Remove users/groups from AWS SSO if not in Google"
    echo "  --log-retention DAYS         CloudWatch log retention days (default: 30)"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -i d-1234567890 -d company.com -e admin@company.com -k /path/to/service-account.json --remove-extra-members"
    echo ""
    echo "🔧 Fixes included in this version:"
    echo "  ✅ Automatic user creation from Google Workspace"
    echo "  ✅ Multi-domain group support (fetches all groups, not just primary domain)"
    echo "  ✅ User cleanup when removed from Google Workspace"
    echo "  ✅ Group cleanup when removed from Google Workspace"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -i|--identity-store-id)
            IDENTITY_STORE_ID="$2"
            shift 2
            ;;
        -d|--domain)
            GOOGLE_DOMAIN="$2"
            shift 2
            ;;
        -e|--admin-email)
            GOOGLE_ADMIN_EMAIL="$2"
            shift 2
            ;;
        -k|--service-account)
            SERVICE_ACCOUNT_FILE="$2"
            shift 2
            ;;
        --schedule)
            SYNC_SCHEDULE="$2"
            shift 2
            ;;
        --include-groups)
            INCLUDE_GROUPS="$2"
            shift 2
            ;;
        --exclude-groups)
            EXCLUDE_GROUPS="$2"
            shift 2
            ;;
        --remove-extra-members)
            REMOVE_EXTRA_MEMBERS="true"
            shift
            ;;
        --log-retention)
            LOG_RETENTION="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check required parameters
if [[ -z "$IDENTITY_STORE_ID" || -z "$GOOGLE_DOMAIN" || -z "$GOOGLE_ADMIN_EMAIL" || -z "$SERVICE_ACCOUNT_FILE" ]]; then
    echo "❌ Missing required parameters!"
    echo ""
    show_usage
    exit 1
fi

# Validate service account file exists
if [[ ! -f "$SERVICE_ACCOUNT_FILE" ]]; then
    echo "❌ Service account file not found: $SERVICE_ACCOUNT_FILE"
    exit 1
fi

echo "🚀 Deploying Enhanced Google Workspace to AWS SSO Group Sync..."
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "Domain: $GOOGLE_DOMAIN"
echo "Admin Email: $GOOGLE_ADMIN_EMAIL"
echo "Identity Store ID: $IDENTITY_STORE_ID"
echo "Remove Extra Members: ${REMOVE_EXTRA_MEMBERS:-false}"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Get AWS Account ID for unique naming
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="${BUCKET_PREFIX}-${ACCOUNT_ID}-${REGION}"

echo "📦 Creating deployment bucket: ${BUCKET_NAME}"

# Create S3 bucket for deployment artifacts
aws s3 mb s3://${BUCKET_NAME} --region ${REGION} 2>/dev/null || echo "Bucket already exists"

# Package CloudFormation template
echo "📋 Packaging CloudFormation template..."
aws cloudformation package \
    --template-file template.yaml \
    --s3-bucket ${BUCKET_NAME} \
    --output-template-file packaged-template.yaml \
    --region ${REGION}

# Build parameter overrides array
PARAMETER_OVERRIDES=(
    "IdentityStoreId=${IDENTITY_STORE_ID}"
    "GoogleDomain=${GOOGLE_DOMAIN}"
    "GoogleAdminEmail=${GOOGLE_ADMIN_EMAIL}"
    "SyncSchedule=${SYNC_SCHEDULE:-rate(15 minutes)}"
    "RemoveExtraMembers=${REMOVE_EXTRA_MEMBERS:-false}"
    "LogRetentionDays=${LOG_RETENTION:-30}"
)

# Handle include/exclude groups separately to avoid CloudFormation CommaDelimitedList issues
if [[ -n "$INCLUDE_GROUPS" ]]; then
    PARAMETER_OVERRIDES+=("IncludeGroups=${INCLUDE_GROUPS}")
else
    PARAMETER_OVERRIDES+=("IncludeGroups=")
fi

if [[ -n "$EXCLUDE_GROUPS" ]]; then
    PARAMETER_OVERRIDES+=("ExcludeGroups=${EXCLUDE_GROUPS}")
else
    PARAMETER_OVERRIDES+=("ExcludeGroups=")
fi

# Deploy CloudFormation stack
echo "🏗️  Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file packaged-template.yaml \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_NAMED_IAM \
    --region ${REGION} \
    --parameter-overrides "${PARAMETER_OVERRIDES[@]}"

# Create Lambda deployment package with dependencies
echo "🔄 Creating Lambda deployment package..."
mkdir -p lambda-package
cp lambda_function.py lambda-package/

# Install dependencies directly into package
echo "📚 Installing dependencies..."
pip install -r requirements.txt -t lambda-package/ --quiet

# Create deployment zip
cd lambda-package && zip -r ../function.zip . && cd ..
rm -rf lambda-package

# Update Lambda function code
echo "⬆️  Updating Lambda function code..."
aws lambda update-function-code \
    --function-name ${STACK_NAME}-sync-function \
    --zip-file fileb://function.zip \
    --region ${REGION}

# Update secret with service account
echo "🔐 Updating secret with Google service account..."

# Create virtual environment for Python dependencies
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install boto3 --quiet

# Update secret
if AWS_DEFAULT_REGION=${REGION} python update-secret.py "${SERVICE_ACCOUNT_FILE}" "${STACK_NAME}"; then
    echo "✅ Secret updated successfully!"
else
    echo "❌ Failed to update secret. Please run manually:"
    echo "   AWS_DEFAULT_REGION=${REGION} python update-secret.py ${SERVICE_ACCOUNT_FILE} ${STACK_NAME}"
    deactivate
    exit 1
fi

# Cleanup virtual environment
deactivate
rm -rf venv

# Get stack outputs
echo "📊 Getting stack outputs..."
aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs'

echo ""
echo "✅ Enhanced deployment completed successfully!"
echo ""
echo "🎉 Your Google Workspace to AWS SSO sync is now active with fixes!"
echo ""
echo "🔧 New Features:"
echo "   ✅ Automatic user creation from Google Workspace"
echo "   ✅ Multi-domain group support"
echo "   ✅ User/group cleanup when removed from Google"
echo ""
echo "📝 Next steps:"
echo "1. Test the Lambda function:"
echo "   aws lambda invoke --function-name ${STACK_NAME}-sync-function response.json --region ${REGION}"
echo ""
echo "2. Monitor logs:"
echo "   aws logs tail /aws/lambda/${STACK_NAME}-sync-function --follow --region ${REGION}"
echo ""
echo "3. Check sync results:"
echo "   cat response.json"
echo ""

# Cleanup
rm -f function.zip packaged-template.yaml