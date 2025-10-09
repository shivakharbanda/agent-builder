"""Quick script to check workflow configuration"""

from workflows.models import Workflow
import json

workflow = Workflow.objects.get(id=20)

print("Workflow Configuration:")
print(json.dumps(workflow.configuration, indent=2))

print("\n\nNodes in configuration:")
nodes = workflow.configuration.get('nodes', [])
for node in nodes:
    print(f"  - ID: {node['id']}, Type: {node['type']}")

print(f"\n\nTotal nodes: {len(nodes)}")
print(f"Total edges: {len(workflow.configuration.get('edges', []))}")
