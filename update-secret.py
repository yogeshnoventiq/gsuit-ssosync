#!/usr/bin/env python3
"""
Script to update AWS Secrets Manager with Google service account credentials
"""

import json
import base64
import boto3
import sys
from pathlib import Path

def get_stack_parameters(stack_name):
    """Get parameters from CloudFormation stack"""
    try:
        # Use region from environment or default
        import os
        region = os.environ.get('AWS_DEFAULT_REGION')
        cf_client = boto3.client('cloudformation', region_name=region)
        response = cf_client.describe_stacks(StackName=stack_name)
        
        parameters = {}
        for param in response['Stacks'][0]['Parameters']:
            parameters[param['ParameterKey']] = param['ParameterValue']
        
        return parameters
    except Exception as e:
        print(f"❌ Error getting stack parameters: {e}")
        return None

def update_secret():
    """Update the secret with Google service account credentials"""
    
    if len(sys.argv) not in [2, 3]:
        print("Usage: python update-secret.py <path-to-service-account.json> [stack-name]")
        print("Default stack name: gsuite-aws-sso-sync")
        sys.exit(1)
    
    service_account_file = sys.argv[1]
    stack_name = sys.argv[2] if len(sys.argv) == 3 else 'gsuite-aws-sso-sync'
    
    try:
        # Get stack parameters
        print(f"📋 Getting parameters from CloudFormation stack: {stack_name}")
        stack_params = get_stack_parameters(stack_name)
        
        if not stack_params:
            print("❌ Could not retrieve stack parameters. Make sure the stack is deployed.")
            sys.exit(1)
        
        # Validate and read service account JSON
        print(f"📖 Reading service account file: {service_account_file}")
        file_path = Path(service_account_file).resolve()
        if not file_path.exists() or not file_path.is_file():
            raise ValueError(f"Invalid service account file: {service_account_file}")
        
        with open(file_path, 'r') as f:
            service_account_json = f.read()
        
        # Encode to base64
        service_account_b64 = base64.b64encode(service_account_json.encode()).decode()
        
        # Parse include/exclude groups from CloudFormation parameters
        include_groups_param = stack_params.get('IncludeGroups', '')
        exclude_groups_param = stack_params.get('ExcludeGroups', '')
        
        # Handle empty string case for CloudFormation CommaDelimitedList
        if include_groups_param and include_groups_param != "":
            include_groups = [g.strip() for g in include_groups_param.split(',') if g.strip()]
        else:
            include_groups = []
            
        if exclude_groups_param and exclude_groups_param != "":
            exclude_groups = [g.strip() for g in exclude_groups_param.split(',') if g.strip()]
        else:
            exclude_groups = []
        
        # Create the secret configuration
        secret_config = {
            "google": {
                "service_account_key_b64": service_account_b64,
                "admin_email": stack_params['GoogleAdminEmail'],
                "domain": stack_params['GoogleDomain'],
                "scopes": [
                    "https://www.googleapis.com/auth/admin.directory.group.readonly",
                    "https://www.googleapis.com/auth/admin.directory.user.readonly"
                ]
            },
            "aws": {
                "identity_store_id": stack_params['IdentityStoreId']
            },
            "sync": {
                "include_groups": include_groups,
                "exclude_groups": exclude_groups,
                "remove_extra_members": stack_params.get('RemoveExtraMembers', 'false').lower() == 'true'
            }
        }
        
        # Update the secret
        print("🔐 Updating AWS Secrets Manager...")
        import os
        region = os.environ.get('AWS_DEFAULT_REGION')
        secrets_client = boto3.client('secretsmanager', region_name=region)
        
        response = secrets_client.update_secret(
            SecretId='gsuite-aws-sso-sync-config',
            SecretString=json.dumps(secret_config, indent=2)
        )
        
        print("✅ Secret updated successfully!")
        print(f"Secret ARN: {response['ARN']}")
        print(f"Version ID: {response['VersionId']}")
        print("\n📊 Configuration Summary:")
        print(f"  Domain: {stack_params['GoogleDomain']}")
        print(f"  Admin Email: {stack_params['GoogleAdminEmail']}")
        print(f"  Identity Store ID: {stack_params['IdentityStoreId']}")
        print(f"  Include Groups: {include_groups or 'All groups'}")
        print(f"  Exclude Groups: {exclude_groups or 'None'}")
        print(f"  Remove Extra Members: {stack_params.get('RemoveExtraMembers', 'false')}")
        
    except FileNotFoundError:
        print(f"❌ Service account file not found: {service_account_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error updating secret: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_secret()