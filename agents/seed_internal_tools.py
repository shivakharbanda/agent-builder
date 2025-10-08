"""
Seed Internal Tools

Populates the database with internal tool definitions.
Run this script to create tool records in the database.

Usage:
    python manage.py shell < agents/seed_internal_tools.py

Or:
    from agents.seed_internal_tools import seed_internal_tools
    seed_internal_tools()
"""

import django
import os
import sys

# Setup Django
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from agents.models import InternalTool
from credentials.models import CredentialType, CredentialCategory
from agents.tools import get_all_tool_metadata


def seed_internal_tools():
    """
    Seed internal tools from the tool registry into the database.

    This function:
    1. Gets all tools from the TOOL_REGISTRY
    2. Creates or updates InternalTool records
    3. Links to appropriate CredentialType if needed
    """
    print("\n" + "="*80)
    print("SEEDING INTERNAL TOOLS")
    print("="*80 + "\n")

    # Get all registered tools
    tools_metadata = get_all_tool_metadata()

    if not tools_metadata:
        print("⚠️  No tools found in registry. Is the registry loaded?")
        return

    print(f"Found {len(tools_metadata)} tools in registry\n")

    tools_created = 0
    tools_updated = 0
    tools_skipped = 0

    for tool_meta in tools_metadata:
        tool_name = tool_meta['display_name'] or tool_meta['tool_name']
        tool_type = tool_meta['tool_name']

        print(f"Processing: {tool_name} ({tool_type})")

        # Get or create credential type if required
        credential_type = None
        if tool_meta['requires_credential'] and tool_meta['required_credential_type']:
            required_cred_type_name = tool_meta['required_credential_type']

            try:
                credential_type = CredentialType.objects.get(type_name=required_cred_type_name)
                print(f"  ✓ Found credential type: {required_cred_type_name}")
            except CredentialType.DoesNotExist:
                print(f"  ⚠️  Credential type '{required_cred_type_name}' not found, creating...")

                # Get or create API category
                api_category, _ = CredentialCategory.objects.get_or_create(
                    name='API',
                    defaults={
                        'description': 'API Services',
                        'icon': 'api'
                    }
                )

                # Create credential type
                credential_type = CredentialType.objects.create(
                    category=api_category,
                    type_name=required_cred_type_name,
                    type_description=f"Credential for {tool_name}"
                )
                print(f"  ✓ Created credential type: {required_cred_type_name}")

                # Create API key field
                from credentials.models import CredentialField
                CredentialField.objects.create(
                    credential_type=credential_type,
                    field_name='API Key',
                    field_type='password',
                    is_required=True,
                    is_secure=True,
                    order=1,
                    placeholder='Enter your API key',
                    help_text=f'Your {required_cred_type_name} API key'
                )
                print(f"  ✓ Created 'API Key' field")

        # Create or update InternalTool
        defaults = {
            'description': tool_meta['description'],
            'category': tool_meta['category'],
            'requires_credential': tool_meta['requires_credential'],
            'required_credential_type': credential_type,
            'input_schema': tool_meta['input_schema'],
            'output_schema': tool_meta['output_schema'],
            'is_enabled': True,
        }

        tool, created = InternalTool.objects.update_or_create(
            tool_type=tool_type,
            defaults={
                'name': tool_name,
                **defaults
            }
        )

        if created:
            tools_created += 1
            print(f"  ✅ Created tool: {tool_name}")
        else:
            tools_updated += 1
            print(f"  ✅ Updated tool: {tool_name}")

    print(f"\n" + "="*80)
    print(f"SEEDING COMPLETE")
    print(f"="*80)
    print(f"Tools created: {tools_created}")
    print(f"Tools updated: {tools_updated}")
    print(f"Tools skipped: {tools_skipped}")
    print(f"Total processed: {len(tools_metadata)}")
    print()


def seed_serp_api_tool_only():
    """
    Seed only the SERP API tool (for quick testing).
    """
    from agents.tools.serp_api import SerpApiTool

    print("\n" + "="*80)
    print("SEEDING SERP API TOOL")
    print("="*80 + "\n")

    # Get or create API category
    api_category, _ = CredentialCategory.objects.get_or_create(
        name='API',
        defaults={
            'description': 'API Services',
            'icon': 'api'
        }
    )

    # Get or create SERP API credential type
    serp_cred_type, created = CredentialType.objects.get_or_create(
        type_name='SERP API',
        defaults={
            'category': api_category,
            'type_description': 'SERP API for web search results'
        }
    )

    if created:
        print("✓ Created SERP API credential type")

        # Create API key field
        from credentials.models import CredentialField
        CredentialField.objects.create(
            credential_type=serp_cred_type,
            field_name='API Key',
            field_type='password',
            is_required=True,
            is_secure=True,
            order=1,
            placeholder='Enter your SERP API key',
            help_text='Your SERP API key from https://serpapi.com/'
        )
        print("✓ Created 'API Key' field")
    else:
        print("✓ SERP API credential type already exists")

    # Create or update tool
    tool, created = InternalTool.objects.update_or_create(
        tool_type='serp_api',
        defaults={
            'name': SerpApiTool.display_name,
            'description': SerpApiTool.description,
            'category': SerpApiTool.category,
            'requires_credential': SerpApiTool.requires_credential,
            'required_credential_type': serp_cred_type,
            'input_schema': SerpApiTool.input_schema,
            'output_schema': SerpApiTool.output_schema,
            'is_enabled': True,
        }
    )

    if created:
        print(f"✅ Created SERP API tool")
    else:
        print(f"✅ Updated SERP API tool")

    print("\n" + "="*80)
    print("SEEDING COMPLETE")
    print("="*80 + "\n")


if __name__ == '__main__':
    # Run full seeding
    seed_internal_tools()

    # Or run SERP API only:
    # seed_serp_api_tool_only()
