"""
Seed script for Node Registry data.

This script populates the NodeCategory and NodeType models with initial data
for all 6 node types across 4 categories.

Usage:
    python manage.py shell < workflows/seed_node_registry.py
    or
    python manage.py shell
    >>> exec(open('workflows/seed_node_registry.py').read())
"""

import django
import os
import sys

# Setup Django environment if running as standalone script
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agent_builder.settings')
    django.setup()

from workflows.models import NodeCategory, NodeType


def seed_node_registry():
    """Seed NodeCategory and NodeType models with initial data."""

    print("Starting node registry seeding...")

    # ========================================================================
    # 1. Create Node Categories
    # ========================================================================

    categories_data = [
        {
            'name': 'data_source',
            'description': 'Nodes that retrieve or generate data from external sources',
            'icon': 'database'
        },
        {
            'name': 'processor',
            'description': 'Nodes that transform, filter, or process data',
            'icon': 'settings'
        },
        {
            'name': 'data_sink',
            'description': 'Nodes that output or store data to destinations',
            'icon': 'save'
        },
        {
            'name': 'control_flow',
            'description': 'Nodes that control workflow execution flow and branching',
            'icon': 'fork_right'
        },
    ]

    categories = {}
    for cat_data in categories_data:
        category, created = NodeCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'description': cat_data['description'],
                'icon': cat_data['icon']
            }
        )
        categories[cat_data['name']] = category
        status = "Created" if created else "Already exists"
        print(f"  {status}: Category '{category.name}'")

    # ========================================================================
    # 2. Create Node Types
    # ========================================================================

    node_types_data = [
        {
            'category': 'data_source',
            'type_name': 'database',
            'type_description': 'Executes SQL queries against configured database credentials',
            'icon': 'storage',
            'handler_class_name': 'DatabaseNode'
        },
        {
            'category': 'processor',
            'type_name': 'agent',
            'type_description': 'Processes data using AI agents with configured prompts',
            'icon': 'smart_toy',
            'handler_class_name': 'AgentNode'
        },
        {
            'category': 'data_sink',
            'type_name': 'output',
            'type_description': 'Saves workflow results to specified destinations',
            'icon': 'upload',
            'handler_class_name': 'OutputNode'
        },
        {
            'category': 'processor',
            'type_name': 'filter',
            'type_description': 'Filters data rows based on conditional logic',
            'icon': 'filter_alt',
            'handler_class_name': 'FilterNode'
        },
        {
            'category': 'processor',
            'type_name': 'script',
            'type_description': 'Executes custom Python or JavaScript code for data transformation',
            'icon': 'code',
            'handler_class_name': 'ScriptNode'
        },
        {
            'category': 'control_flow',
            'type_name': 'conditional',
            'type_description': 'Branches workflow execution based on condition evaluation',
            'icon': 'call_split',
            'handler_class_name': 'ConditionalNode'
        },
    ]

    for node_data in node_types_data:
        category = categories[node_data['category']]

        node_type, created = NodeType.objects.get_or_create(
            type_name=node_data['type_name'],
            defaults={
                'category': category,
                'type_description': node_data['type_description'],
                'icon': node_data['icon'],
                'handler_class_name': node_data['handler_class_name']
            }
        )
        status = "Created" if created else "Already exists"
        print(f"  {status}: NodeType '{node_type.type_name}' -> {node_type.handler_class_name}")

    print("\nNode registry seeding completed!")
    print(f"Total Categories: {NodeCategory.objects.count()}")
    print(f"Total Node Types: {NodeType.objects.count()}")

    # Display summary
    print("\n" + "="*60)
    print("NODE REGISTRY SUMMARY")
    print("="*60)
    for category in NodeCategory.objects.all():
        print(f"\n{category.name.upper()} ({category.node_types.count()} types):")
        for node_type in category.node_types.all():
            print(f"  - {node_type.type_name}: {node_type.handler_class_name}")


if __name__ == '__main__':
    seed_node_registry()
