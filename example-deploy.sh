#!/bin/bash

# Example deployment script showing different configuration options

echo "🚀 Google Workspace to AWS SSO Group Sync - Example Deployments"
echo ""

# Example 1: Basic deployment
echo "📋 Example 1: Basic deployment"
echo "./deploy.sh \\"
echo "  --identity-store-id d-1234567890 \\"
echo "  --domain company.com \\"
echo "  --admin-email admin@company.com \\"
echo "  --service-account /path/to/service-account.json"
echo ""

# Example 2: With group filtering
echo "📋 Example 2: With group filtering and notifications"
echo "./deploy.sh \\"
echo "  --identity-store-id d-1234567890 \\"
echo "  --domain company.com \\"
echo "  --admin-email admin@company.com \\"
echo "  --service-account /path/to/service-account.json \\"
echo "  --include-groups \"Engineering,Marketing,Sales\" \\"
echo "  --schedule \"rate(2 hours)\""
echo ""

# Example 3: With exclusions and custom settings
echo "📋 Example 3: With exclusions and custom settings"
echo "./deploy.sh \\"
echo "  --stack-name my-gsuite-sync \\"
echo "  --region us-west-2 \\"
echo "  --identity-store-id d-1234567890 \\"
echo "  --domain company.com \\"
echo "  --admin-email admin@company.com \\"
echo "  --service-account /path/to/service-account.json \\"
echo "  --exclude-groups \"admin-only,test-groups\" \\"
echo "  --remove-extra-members \\"
echo "  --log-retention 90"
echo ""

# Example 4: Production deployment with all options
echo "📋 Example 4: Production deployment with all options"
echo "./deploy.sh \\"
echo "  --stack-name prod-gsuite-aws-sso-sync \\"
echo "  --region us-east-1 \\"
echo "  --identity-store-id d-1234567890 \\"
echo "  --domain company.com \\"
echo "  --admin-email admin@company.com \\"
echo "  --service-account /path/to/service-account.json \\"
echo "  --schedule \"cron(0 9 * * ? *)\" \\"
echo "  --exclude-groups \"admin-only,contractors\" \\"
echo "  --remove-extra-members \\"
echo "  --log-retention 365"
echo ""

echo "💡 Tips:"
echo "• Get your Identity Store ID: aws sso-admin list-instances"
echo "• Schedule expressions: rate(X hours/days) or cron(0 9 * * ? *)"
echo "• Use --help for full parameter list"