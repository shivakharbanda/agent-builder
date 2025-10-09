"""
Test Script for Pydantic AI Graph Workflow Execution

Run this with: python manage.py shell < test_pydantic_graph.py
Or in Django shell: exec(open('test_pydantic_graph.py').read())
"""

import asyncio
from workflows.models import Workflow, WorkflowExecution
from workflows.execution.graph_executor import execute_workflow_with_graph


def test_graph_builder():
    """Test 1: Build graph from workflow"""
    print("\n" + "="*80)
    print("TEST 1: Building Pydantic Graph from Workflow")
    print("="*80)

    # Get your chat workflow (ID 20)
    try:
        workflow = Workflow.objects.get(id=20)
        print(f"✓ Found workflow: {workflow.name} (ID: {workflow.id})")
    except Workflow.DoesNotExist:
        print("✗ Workflow ID 20 not found. Please update the ID.")
        return False

    # Build graph
    from workflows.execution.graph_builder import WorkflowGraphBuilder

    builder = WorkflowGraphBuilder(workflow=workflow, execution_id=0)

    try:
        graph = builder.build()
        print(f"✓ Graph built successfully")
        print(f"  - Nodes in registry: {len(builder.node_registry)}")
        print(f"  - Node types: {[n.node_type for n in builder.node_registry.values()]}")

        start_node = builder.get_start_node()
        if start_node:
            print(f"✓ Start node found: {start_node.node_id} ({start_node.node_type})")
        else:
            print("✗ No start node found")
            return False

        # Generate visualization
        mermaid = builder.visualize()
        print(f"\n✓ Mermaid diagram generated:")
        print(mermaid)

        return True

    except Exception as e:
        print(f"✗ Error building graph: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_execution():
    """Test 2: Execute full workflow"""
    print("\n" + "="*80)
    print("TEST 2: Full Workflow Execution")
    print("="*80)

    # Get workflow
    try:
        workflow = Workflow.objects.get(id=20)
    except Workflow.DoesNotExist:
        print("✗ Workflow ID 20 not found")
        return False

    # Create execution record
    execution = WorkflowExecution.objects.create(
        workflow=workflow,
        status='pending',
        execution_type='full_workflow',
        triggered_by='manual'
    )

    print(f"✓ Created execution record: {execution.id}")

    # Execute using graph
    try:
        print(f"\n▶ Starting execution...")
        final_state = asyncio.run(execute_workflow_with_graph(execution.id))

        print(f"\n✓ Execution completed successfully!")
        print(f"  - Nodes executed: {len(final_state.node_execution_order)}")
        print(f"  - Execution order: {final_state.node_execution_order}")
        print(f"  - Final data type: {type(final_state.current_data)}")

        if isinstance(final_state.current_data, list) and final_state.current_data:
            print(f"  - Sample output: {final_state.current_data[0]}")
        elif isinstance(final_state.current_data, dict):
            print(f"  - Output keys: {list(final_state.current_data.keys())}")

        # Check execution record
        execution.refresh_from_db()
        print(f"\n✓ Execution record updated:")
        print(f"  - Status: {execution.status}")
        print(f"  - Progress: {execution.progress_percentage}%")
        print(f"  - Message: {execution.progress_message}")

        return True

    except Exception as e:
        print(f"\n✗ Execution failed: {e}")
        import traceback
        traceback.print_exc()

        execution.refresh_from_db()
        print(f"\nExecution record status: {execution.status}")
        print(f"Error message: {execution.error_message}")

        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "#"*80)
    print("# Pydantic AI Graph Workflow Execution - Test Suite")
    print("#"*80)

    results = []

    # Test 1: Build graph
    results.append(("Build Graph", test_graph_builder()))

    # Test 2: Full execution
    results.append(("Full Execution", test_full_execution()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Pydantic Graph execution is working!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")


if __name__ == '__main__':
    run_all_tests()
