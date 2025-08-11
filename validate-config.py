#!/usr/bin/env python3
"""
Configuration validation script for Google Workspace to AWS SSO sync
"""

import re
import sys

import boto3

def validate_identity_store_id(identity_store_id):
    """Validate AWS SSO Identity Store ID format and existence"""
    # Check format
    if not re.match(r'^d-[0-9a-f]{10}$', identity_store_id):
        return False, "Invalid format. Should be d-xxxxxxxxxx"

    # Check if it exists
    try:
        client = boto3.client('identitystore')
        client.list_users(IdentityStoreId=identity_store_id, MaxResults=1)
        return True, "Valid and accessible"
    except Exception as e:
        return False, f"Cannot access: {str(e)}"

def validate_domain(domain):
    """Validate domain format"""
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$'
    if re.match(pattern, domain):
        return True, "Valid domain format"
    return False, "Invalid domain format"

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, "Valid email format"
    return False, "Invalid email format"

def validate_schedule(schedule):
    """Validate EventBridge schedule expression"""
    rate_pattern = r'^rate\(\d+\s+(minute|minutes|hour|hours|day|days)\)$'
    cron_pattern = r'^cron\([0-9*,/-]+\s+[0-9*,/-]+\s+[0-9*,/-]+\s+[0-9*,/-]+\s+[0-9*,?/-]+\s+[0-9*,?/-]+\)$'

    if re.match(rate_pattern, schedule) or re.match(cron_pattern, schedule):
        return True, "Valid schedule expression"
    return False, "Invalid schedule expression"

def check_aws_permissions():
    """Check if AWS credentials have required permissions"""
    try:
        # Test basic AWS access
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()

        # Test required services
        services_to_test = [
            ('cloudformation', 'list_stacks'),
            ('lambda', 'list_functions'),
            ('secretsmanager', 'list_secrets'),
            ('identitystore', 'list_users'),
            ('events', 'list_rules'),
            ('sns', 'list_topics'),
            ('logs', 'describe_log_groups'),
            ('s3', 'list_buckets')
        ]

        failed_services = []
        for service, operation in services_to_test:
            try:
                client = boto3.client(service)
                # Try a basic read operation
                if service == 'identitystore':
                    continue  # Skip for now, will test with actual ID
                elif service == 'cloudformation':
                    client.list_stacks(MaxResults=1)
                elif service == 'lambda':
                    client.list_functions(MaxItems=1)
                elif service == 'secretsmanager':
                    client.list_secrets(MaxResults=1)
                elif service == 'events':
                    client.list_rules(Limit=1)
                elif service == 'sns':
                    client.list_topics()
                elif service == 'logs':
                    client.describe_log_groups(limit=1)
                elif service == 's3':
                    client.list_buckets()
            except Exception:
                failed_services.append(service)

        if failed_services:
            return False, f"Missing permissions for: {', '.join(failed_services)}"

        return True, f"AWS access validated for account: {identity['Account']}"

    except Exception as e:
        return False, f"AWS access failed: {str(e)}"

def main():
    """Main validation function"""
    if len(sys.argv) < 4:
        print("Usage: python validate-config.py <identity-store-id> <domain> <admin-email> [schedule]")
        print("Example: python validate-config.py d-1234567890 company.com admin@company.com")
        sys.exit(1)

    identity_store_id = sys.argv[1]
    domain = sys.argv[2]
    admin_email = sys.argv[3]
    schedule = sys.argv[4] if len(sys.argv) > 4 else "rate(6 hours)"

    print("🔍 Validating Google Workspace to AWS SSO Sync Configuration...")
    print("")

    # Validate AWS permissions
    print("1. Checking AWS permissions...")
    aws_valid, aws_msg = check_aws_permissions()
    print(f"   {'✅' if aws_valid else '❌'} {aws_msg}")

    # Validate Identity Store ID
    print("2. Validating Identity Store ID...")
    id_valid, id_msg = validate_identity_store_id(identity_store_id)
    print(f"   {'✅' if id_valid else '❌'} {id_msg}")

    # Validate domain
    print("3. Validating domain...")
    domain_valid, domain_msg = validate_domain(domain)
    print(f"   {'✅' if domain_valid else '❌'} {domain_msg}")

    # Validate email
    print("4. Validating admin email...")
    email_valid, email_msg = validate_email(admin_email)
    print(f"   {'✅' if email_valid else '❌'} {email_msg}")

    # Validate schedule
    print("5. Validating schedule expression...")
    schedule_valid, schedule_msg = validate_schedule(schedule)
    print(f"   {'✅' if schedule_valid else '❌'} {schedule_msg}")

    print("")

    # Overall result
    all_valid = all([aws_valid, id_valid, domain_valid, email_valid, schedule_valid])

    if all_valid:
        print("✅ All validations passed! You can proceed with deployment.")
        print("")
        print("📋 Suggested deployment command:")
        print("./deploy.sh \\")
        print(f"  --identity-store-id {identity_store_id} \\")
        print(f"  --domain {domain} \\")
        print(f"  --admin-email {admin_email}")
        if schedule != "rate(6 hours)":
            print("  --schedule \"{schedule}\"")
    else:
        print("❌ Some validations failed. Please fix the issues above before deployment.")
        sys.exit(1)

if __name__ == "__main__":
    main()
