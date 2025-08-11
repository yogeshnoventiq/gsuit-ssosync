import json
import boto3
import logging
import base64
from typing import Dict, List, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class GSuiteAWSSSOSync:
    def __init__(self):
        """Initialize the sync service with AWS services"""
        self.secrets_client = boto3.client('secretsmanager')
        self.identity_store = boto3.client('identitystore')

        # Load configuration from Secrets Manager
        self.config = self._load_config()
        self.identity_store_id = self.config['aws']['identity_store_id']

        # Initialize Google Workspace client
        self.google_service = self._init_google_service()

    def _load_config(self) -> Dict:
        """Load configuration from AWS Secrets Manager"""
        try:
            secret_name = "gsuite-aws-sso-sync-config"
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except Exception as e:
            logger.error(f"Error loading config from Secrets Manager: {e}")
            raise

    def _init_google_service(self):
        """Initialize Google Workspace Admin SDK service"""
        try:
            # Decode base64 service account key
            service_account_b64 = self.config['google']['service_account_key_b64']
            service_account_json = base64.b64decode(service_account_b64).decode('utf-8')
            service_account_info = json.loads(service_account_json)

            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=self.config['google']['scopes']
            )

            # Use domain-wide delegation
            delegated_credentials = credentials.with_subject(
                self.config['google']['admin_email']
            )

            return build('admin', 'directory_v1', credentials=delegated_credentials)
        except Exception as e:
            logger.error(f"Error initializing Google service: {e}")
            raise

    def get_google_groups(self) -> List[Dict]:
        """Fetch all groups from Google Workspace"""
        logger.info("Fetching groups from Google Workspace...")
        groups = []

        try:
            request = self.google_service.groups().list(
                domain=self.config['google']['domain']
            )

            while request is not None:
                response = request.execute()
                groups.extend(response.get('groups', []))
                request = self.google_service.groups().list_next(request, response)

        except Exception as e:
            logger.error(f"Error fetching Google groups: {e}")
            return []

        logger.info(f"Found {len(groups)} groups in Google Workspace")
        return groups

    def get_google_group_members(self, group_email: str) -> List[Dict]:
        """Fetch members of a specific Google group"""
        members = []

        try:
            request = self.google_service.members().list(groupKey=group_email)

            while request is not None:
                response = request.execute()
                members.extend(response.get('members', []))
                request = self.google_service.members().list_next(request, response)

        except Exception as e:
            logger.error(f"Error fetching members for group {group_email}: {e}")
            return []

        return members

    def get_aws_groups(self) -> Dict[str, str]:
        """Fetch all groups from AWS SSO Identity Store"""
        logger.info("Fetching groups from AWS SSO...")
        groups = {}

        try:
            paginator = self.identity_store.get_paginator('list_groups')

            for page in paginator.paginate(IdentityStoreId=self.identity_store_id):
                for group in page['Groups']:
                    groups[group['DisplayName']] = group['GroupId']

        except Exception as e:
            logger.error(f"Error fetching AWS SSO groups: {e}")
            return {}

        logger.info(f"Found {len(groups)} groups in AWS SSO")
        return groups

    def get_aws_users(self) -> Dict[str, str]:
        """Fetch all users from AWS SSO Identity Store"""
        logger.info("Fetching users from AWS SSO...")
        users = {}

        try:
            paginator = self.identity_store.get_paginator('list_users')

            for page in paginator.paginate(IdentityStoreId=self.identity_store_id):
                for user in page['Users']:
                    for email in user.get('Emails', []):
                        if email.get('Primary', False):
                            users[email['Value']] = user['UserId']
                            break

        except Exception as e:
            logger.error(f"Error fetching AWS SSO users: {e}")
            return {}

        logger.info(f"Found {len(users)} users in AWS SSO")
        return users

    def create_aws_group(self, group_name: str, description: str = "") -> Optional[str]:
        """Create a new group in AWS SSO"""
        try:
            response = self.identity_store.create_group(
                IdentityStoreId=self.identity_store_id,
                DisplayName=group_name,
                Description=description or f"Synced from Google Workspace: {group_name}"
            )

            group_id = response['GroupId']
            logger.info(f"Created AWS SSO group: {group_name} ({group_id})")
            return group_id

        except ClientError as e:
            if e.response['Error']['Code'] == 'ConflictException':
                logger.warning(f"Group {group_name} already exists")
                return None
            else:
                logger.error(f"Error creating group {group_name}: {e}")
                return None

    def get_aws_group_members(self, group_id: str) -> List[str]:
        """Get current members of an AWS SSO group"""
        members = []

        try:
            paginator = self.identity_store.get_paginator('list_group_memberships')

            for page in paginator.paginate(
                IdentityStoreId=self.identity_store_id,
                GroupId=group_id
            ):
                for membership in page['GroupMemberships']:
                    members.append(membership['MemberId']['UserId'])

        except Exception as e:
            logger.error(f"Error fetching group members for {group_id}: {e}")
            return []

        return members

    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add a user to an AWS SSO group"""
        try:
            self.identity_store.create_group_membership(
                IdentityStoreId=self.identity_store_id,
                GroupId=group_id,
                MemberId={'UserId': user_id}
            )
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == 'ConflictException':
                return True
            else:
                logger.error(f"Error adding user {user_id} to group {group_id}: {e}")
                return False

    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Remove a user from an AWS SSO group"""
        try:
            paginator = self.identity_store.get_paginator('list_group_memberships')

            for page in paginator.paginate(
                IdentityStoreId=self.identity_store_id,
                GroupId=group_id
            ):
                for membership in page['GroupMemberships']:
                    if membership['MemberId']['UserId'] == user_id:
                        self.identity_store.delete_group_membership(
                            IdentityStoreId=self.identity_store_id,
                            MembershipId=membership['MembershipId']
                        )
                        return True

            return False

        except Exception as e:
            logger.error(f"Error removing user {user_id} from group {group_id}: {e}")
            return False

    def sync_groups(self):
        """Main sync function"""
        logger.info("Starting Google Workspace to AWS SSO group sync...")

        # Get data from both systems
        google_groups = self.get_google_groups()
        aws_groups = self.get_aws_groups()
        aws_users = self.get_aws_users()

        if not google_groups:
            logger.error("No Google groups found. Exiting.")
            return

        if not aws_users:
            logger.error("No AWS SSO users found. Exiting.")
            return

        # Filter groups based on configuration
        groups_to_sync = []
        if self.config.get('sync', {}).get('include_groups'):
            include_list = self.config['sync']['include_groups']
            groups_to_sync = [g for g in google_groups if g['name'] in include_list]
        elif self.config.get('sync', {}).get('exclude_groups'):
            exclude_list = self.config['sync']['exclude_groups']
            groups_to_sync = [g for g in google_groups if g['name'] not in exclude_list]
        else:
            groups_to_sync = google_groups

        logger.info(f"Syncing {len(groups_to_sync)} groups...")

        for google_group in groups_to_sync:
            group_name = google_group['name']
            group_email = google_group['email']

            logger.info(f"Processing group: {group_name}")

            # Create group in AWS SSO if it doesn't exist
            if group_name not in aws_groups:
                group_id = self.create_aws_group(
                    group_name,
                    google_group.get('description', '')
                )
                if group_id:
                    aws_groups[group_name] = group_id
                else:
                    continue
            else:
                group_id = aws_groups[group_name]

            # Get members from both systems
            google_members = self.get_google_group_members(group_email)
            aws_member_ids = set(self.get_aws_group_members(group_id))

            # Convert Google members to AWS user IDs
            google_member_ids = set()
            for member in google_members:
                if member['type'] == 'USER':
                    member_email = member['email']
                    if member_email in aws_users:
                        google_member_ids.add(aws_users[member_email])
                    else:
                        logger.warning(f"User {member_email} not found in AWS SSO")

            # Add missing members
            to_add = google_member_ids - aws_member_ids
            for user_id in to_add:
                if self.add_user_to_group(user_id, group_id):
                    logger.info(f"Added user {user_id} to group {group_name}")

            # Remove extra members (if configured)
            if self.config.get('sync', {}).get('remove_extra_members', False):
                to_remove = aws_member_ids - google_member_ids
                for user_id in to_remove:
                    if self.remove_user_from_group(user_id, group_id):
                        logger.info(f"Removed user {user_id} from group {group_name}")

        logger.info("Group sync completed successfully!")

def lambda_handler(event, context):
    """Lambda function handler"""
    try:
        sync_service = GSuiteAWSSSOSync()
        sync_service.sync_groups()

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Group sync completed successfully',
                'timestamp': context.aws_request_id
            })
        }
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': context.aws_request_id
            })
        }
