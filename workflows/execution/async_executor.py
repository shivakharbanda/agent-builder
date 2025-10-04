"""
Asynchronous Workflow Executor

Handles background execution of workflows and individual nodes.
Supports both single node execution and full workflow execution.
"""

import threading
from django.utils import timezone
from workflows.models import WorkflowExecution, NodeExecution, WorkflowNode


def execute_workflow_async(execution_id: int):
    """
    Execute workflow (single node or full) asynchronously.

    This is the main entry point called from a background thread.
    Determines execution type and delegates to appropriate handler.

    Args:
        execution_id: ID of WorkflowExecution record
    """
    try:
        execution = WorkflowExecution.objects.get(id=execution_id)

        if execution.execution_type == 'single_node':
            _execute_single_node(execution)
        else:
            _execute_full_workflow(execution)

    except WorkflowExecution.DoesNotExist:
        print(f"ERROR: WorkflowExecution {execution_id} not found")
    except Exception as e:
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
            execution.status = 'failed'
            execution.error_message = f"Unexpected error: {str(e)}"
            execution.completed_at = timezone.now()
            execution.save()
        except:
            print(f"ERROR: Failed to update execution {execution_id}: {str(e)}")


def _execute_single_node(execution: WorkflowExecution):
    """
    Execute a single node.

    Args:
        execution: WorkflowExecution instance with execution_type='single_node'
    """
    from workflows.execution.node_handlers.factory import NodeFactory

    execution.status = 'running'
    execution.started_at = timezone.now()
    execution.progress_message = f'Executing node {execution.target_node_id}...'
    execution.progress_percentage = 0.0
    execution.save()

    # Create NodeExecution record
    node_exec = NodeExecution.objects.create(
        workflow_execution=execution,
        node_id=execution.target_node_id,
        node_type='unknown',
        status='pending',
        started_at=timezone.now()
    )

    try:
        # Get workflow node
        workflow_node = WorkflowNode.objects.get(
            id=execution.target_node_id,
            workflow=execution.workflow,
            is_active=True
        )

        node_exec.node_type = workflow_node.node_type
        node_exec.status = 'running'
        node_exec.save()

        execution.progress_percentage = 25.0
        execution.save()

        # Determine if this node needs upstream data
        processor_node_types = ['agent', 'filter', 'script', 'conditional', 'output']
        needs_input = workflow_node.node_type in processor_node_types

        input_data = None

        if needs_input:
            # Get upstream data (reuse logic from views.py)
            input_data = _get_upstream_data(execution.workflow, execution.target_node_id)

        execution.progress_percentage = 50.0
        execution.progress_message = f'Processing {workflow_node.node_type} node...'
        execution.save()

        # Create and execute node instance
        node_instance = NodeFactory.create_node(
            node_id=workflow_node.id,
            node_type=workflow_node.node_type,
            configuration=workflow_node.configuration,
            workflow_id=execution.workflow.id,
            execution_id=execution.id,
            position=workflow_node.position
        )

        # Execute the node
        results = node_instance.run(input_data)

        # Success
        node_exec.status = 'completed'
        node_exec.completed_at = timezone.now()
        node_exec.results = results
        node_exec.execution_time_seconds = (
            node_exec.completed_at - node_exec.started_at
        ).total_seconds()
        node_exec.save()

        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.execution_log = {
            'node_id': execution.target_node_id,
            'node_type': workflow_node.node_type,
            'results_count': len(results) if isinstance(results, list) else 1
        }
        execution.progress_percentage = 100.0
        execution.progress_message = 'Node execution completed successfully'
        execution.save()

    except WorkflowNode.DoesNotExist:
        node_exec.status = 'failed'
        node_exec.error_message = f'Node {execution.target_node_id} not found'
        node_exec.completed_at = timezone.now()
        node_exec.save()

        execution.status = 'failed'
        execution.error_message = f'Node {execution.target_node_id} not found in workflow'
        execution.completed_at = timezone.now()
        execution.save()

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        node_exec.status = 'failed'
        node_exec.error_message = str(e)
        node_exec.completed_at = timezone.now()
        node_exec.save()

        execution.status = 'failed'
        execution.error_message = str(e)
        execution.execution_log = {'error_details': error_details}
        execution.completed_at = timezone.now()
        execution.save()


def _execute_full_workflow(execution: WorkflowExecution):
    """
    Execute entire workflow (all nodes in topological order).

    Args:
        execution: WorkflowExecution instance with execution_type='full_workflow'
    """
    from workflows.execution.node_handlers.factory import NodeFactory

    execution.status = 'running'
    execution.started_at = timezone.now()
    execution.progress_message = 'Starting workflow execution...'
    execution.progress_percentage = 0.0
    execution.save()

    try:
        # Get all nodes for this workflow
        nodes = WorkflowNode.objects.filter(
            workflow=execution.workflow,
            is_active=True
        ).order_by('position')

        total_nodes = nodes.count()

        if total_nodes == 0:
            execution.status = 'completed'
            execution.completed_at = timezone.now()
            execution.progress_percentage = 100.0
            execution.progress_message = 'No nodes to execute'
            execution.save()
            return

        completed_nodes = 0
        node_results = {}  # Store results for passing between nodes

        # Execute nodes in order (simple sequential for now)
        # TODO: Later implement topological sort based on edges
        for node in nodes:
            execution.current_node_id = node.id
            execution.progress_message = f'Executing {node.node_type} node (position {node.position})...'
            execution.progress_percentage = (completed_nodes / total_nodes) * 100
            execution.save()

            # Create NodeExecution record
            node_exec = NodeExecution.objects.create(
                workflow_execution=execution,
                node_id=node.id,
                node_type=node.node_type,
                status='running',
                started_at=timezone.now()
            )

            try:
                # Create node instance
                node_instance = NodeFactory.create_node(
                    node_id=node.id,
                    node_type=node.node_type,
                    configuration=node.configuration,
                    workflow_id=execution.workflow.id,
                    execution_id=execution.id,
                    position=node.position
                )

                # Determine input data based on node type
                processor_node_types = ['agent', 'filter', 'script', 'conditional', 'output']
                if node.node_type in processor_node_types and node_results:
                    # Use results from previous node
                    input_data = list(node_results.values())[-1] if node_results else None
                else:
                    input_data = None

                # Execute node
                results = node_instance.run(input_data)

                # Store results for next node
                node_results[node.id] = results

                # Update node execution
                node_exec.status = 'completed'
                node_exec.completed_at = timezone.now()
                node_exec.results = results
                node_exec.execution_time_seconds = (
                    node_exec.completed_at - node_exec.started_at
                ).total_seconds()
                node_exec.save()

                completed_nodes += 1

            except Exception as e:
                import traceback

                node_exec.status = 'failed'
                node_exec.error_message = str(e)
                node_exec.completed_at = timezone.now()
                node_exec.save()

                # Fail entire workflow if one node fails
                raise Exception(f"Node {node.id} ({node.node_type}) failed: {str(e)}")

        # All nodes completed successfully
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.progress_percentage = 100.0
        execution.progress_message = f'Workflow completed successfully ({completed_nodes} nodes)'
        execution.execution_log = {
            'total_nodes': total_nodes,
            'completed_nodes': completed_nodes
        }
        execution.save()

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        execution.status = 'failed'
        execution.error_message = str(e)
        execution.execution_log = {'error_details': error_details}
        execution.completed_at = timezone.now()
        execution.save()


def _get_upstream_data(workflow, target_node_id):
    """
    Get upstream data for a node by executing its dependencies.
    Reuses logic from views.py execute endpoint.

    Args:
        workflow: Workflow instance
        target_node_id: ID of target node

    Returns:
        Input data from upstream nodes
    """
    from workflows.execution.node_handlers.factory import NodeFactory

    # Build mapping from visual node IDs to database node IDs
    visual_to_db_map = {}
    db_to_visual_map = {}

    visual_nodes = workflow.configuration.get('nodes', [])
    db_nodes = WorkflowNode.objects.filter(workflow=workflow, is_active=True).order_by('position')

    # Match nodes by type and configuration keys
    for visual_node in visual_nodes:
        visual_id = visual_node.get('id')
        visual_type = visual_node.get('type')
        visual_config = visual_node.get('config', {})

        # Find matching database node
        for db_node in db_nodes:
            if db_node.node_type != visual_type:
                continue

            # Match by key configuration fields
            if visual_type == 'database' and visual_config.get('credential_id') == db_node.configuration.get('credential_id'):
                visual_to_db_map[visual_id] = db_node.id
                db_to_visual_map[db_node.id] = visual_id
                break
            elif visual_type == 'agent' and visual_config.get('agent_id') == db_node.configuration.get('agent_id'):
                visual_to_db_map[visual_id] = db_node.id
                db_to_visual_map[db_node.id] = visual_id
                break
            elif visual_type == 'output' and visual_config.get('table_name') == db_node.configuration.get('table_name'):
                visual_to_db_map[visual_id] = db_node.id
                db_to_visual_map[db_node.id] = visual_id
                break
            elif visual_type in ['filter', 'script', 'conditional']:
                visual_to_db_map[visual_id] = db_node.id
                db_to_visual_map[db_node.id] = visual_id
                break

    # Get visual node ID for the target node
    target_visual_id = db_to_visual_map.get(target_node_id)
    if not target_visual_id:
        return None

    # Get workflow edges from configuration
    edges = workflow.configuration.get('edges', [])

    # Find upstream nodes
    upstream_edges = [edge for edge in edges if edge.get('target') == target_visual_id]

    if not upstream_edges:
        return None

    # Execute upstream nodes and collect results
    upstream_results = {}

    for edge in upstream_edges:
        source_visual_id = edge.get('source', '')
        source_db_id = visual_to_db_map.get(source_visual_id)

        if not source_db_id:
            continue

        try:
            # Get source node
            source_node = WorkflowNode.objects.get(
                id=source_db_id,
                workflow=workflow,
                is_active=True
            )

            # Create and execute source node instance
            source_instance = NodeFactory.create_node(
                node_id=source_node.id,
                node_type=source_node.node_type,
                configuration=source_node.configuration,
                workflow_id=workflow.id,
                execution_id=0,
                position=source_node.position
            )

            # Execute source node
            source_results = source_instance.run()
            upstream_results[source_visual_id] = source_results

        except (WorkflowNode.DoesNotExist, Exception) as e:
            print(f"ERROR: Failed to execute upstream node {source_visual_id}: {e}")
            continue

    # Return first upstream result (for agent nodes)
    if upstream_results:
        return list(upstream_results.values())[0]

    return None
