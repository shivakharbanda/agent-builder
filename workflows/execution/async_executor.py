"""
Pydantic AI Graph-based Workflow Executor

Handles background execution of workflows using Pydantic AI Graph.
Supports both single node execution and full workflow execution.
"""

import threading
from django.utils import timezone
from workflows.models import WorkflowExecution, NodeExecution, WorkflowNode
from workflows.execution.graph_executor import execute_workflow_sync


def execute_workflow_async(execution_id: int):
    """
    Execute workflow using Pydantic AI Graph asynchronously.

    This is the main entry point called from a background thread.
    Uses Pydantic Graph for full workflow execution.

    Args:
        execution_id: ID of WorkflowExecution record
    """
    try:
        execution = WorkflowExecution.objects.get(id=execution_id)

        if execution.execution_type == 'single_node':
            # Single node execution still uses old method (for now)
            # TODO: Implement single node execution with graph
            _execute_single_node(execution)
        else:
            # Full workflow execution uses Pydantic Graph
            print(f"\n[ASYNC EXECUTOR] Starting Pydantic Graph execution for {execution_id}")
            execute_workflow_sync(execution_id)

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

    Workflow execution flow:
    1. Find and execute trigger node first (if present)
    2. Execute remaining nodes in order, passing data from trigger

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

        # Separate trigger nodes from other nodes
        trigger_node_types = ['trigger_manual', 'trigger_schedule', 'trigger_chat']
        trigger_nodes = [n for n in nodes if n.node_type in trigger_node_types]
        processing_nodes = [n for n in nodes if n.node_type not in trigger_node_types]

        # Execute trigger node first (if present)
        trigger_results = None
        if trigger_nodes:
            trigger_node = trigger_nodes[0]  # Use first trigger node (should only be one)

            execution.current_node_id = trigger_node.id
            execution.progress_message = f'Executing trigger: {trigger_node.node_type}...'
            execution.progress_percentage = (completed_nodes / total_nodes) * 100
            execution.save()

            # Update triggered_by based on trigger node type
            if trigger_node.node_type == 'trigger_manual':
                execution.triggered_by = 'manual'
            elif trigger_node.node_type == 'trigger_schedule':
                execution.triggered_by = 'schedule'
            elif trigger_node.node_type == 'trigger_chat':
                execution.triggered_by = 'chat'
            execution.save()

            # Create NodeExecution record for trigger
            node_exec = NodeExecution.objects.create(
                workflow_execution=execution,
                node_id=trigger_node.id,
                node_type=trigger_node.node_type,
                status='running',
                started_at=timezone.now()
            )

            try:
                # Create and execute trigger node
                trigger_instance = NodeFactory.create_node(
                    node_id=trigger_node.id,
                    node_type=trigger_node.node_type,
                    configuration=trigger_node.configuration,
                    workflow_id=execution.workflow.id,
                    execution_id=execution.id,
                    position=trigger_node.position
                )

                # Execute trigger (no input data)
                trigger_results = trigger_instance.run()

                # Store trigger results
                node_results[trigger_node.id] = trigger_results

                # Update node execution
                node_exec.status = 'completed'
                node_exec.completed_at = timezone.now()
                node_exec.results = trigger_results
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

                raise Exception(f"Trigger node {trigger_node.id} ({trigger_node.node_type}) failed: {str(e)}")

        # Execute remaining nodes in order
        for node in processing_nodes:
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
                processor_node_types = ['agent', 'filter', 'script', 'conditional', 'output', 'internal_tool']
                if node.node_type in processor_node_types:
                    # If this is the first processing node after trigger, use trigger results
                    # Otherwise use results from previous node
                    if trigger_results and not any(n.id in node_results for n in processing_nodes[:processing_nodes.index(node)]):
                        input_data = trigger_results
                    elif node_results:
                        input_data = list(node_results.values())[-1]
                    else:
                        input_data = None
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
            'completed_nodes': completed_nodes,
            'had_trigger': len(trigger_nodes) > 0
        }
        execution.save()

        # If this was a chat-triggered workflow, update conversation with response
        if execution.triggered_by == 'chat':
            _update_chat_conversation_with_response(execution, node_results)

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
    Separates data inputs (to iterate over) from context inputs (reference data).

    Args:
        workflow: Workflow instance
        target_node_id: ID of target node (backend database ID)

    Returns:
        dict: {
            'data': [...],      # Rows to process (from data-input handle)
            'context': {...}    # Reference data (from context-input handle)
        }
        OR list for backward compatibility (if no context edges)
    """
    from workflows.execution.node_handlers.factory import NodeFactory

    # Get workflow edges from configuration (edges now use backend IDs directly)
    edges = workflow.configuration.get('edges', [])

    # Find upstream edges pointing to target node (target is now backend ID)
    upstream_edges = [edge for edge in edges if edge.get('target') == target_node_id]

    if not upstream_edges:
        return None

    # Separate data edges from context edges
    data_edges = []
    context_edges = []

    for edge in upstream_edges:
        target_handle = edge.get('targetHandle')
        if target_handle == 'context-input':
            context_edges.append(edge)
        else:
            # No targetHandle or 'data-input' - treat as data edge (backward compatibility)
            data_edges.append(edge)

    # DEBUG LOGGING
    print(f"\n{'='*80}")
    print(f"[UPSTREAM DATA DEBUG] Target node: {target_node_id}")
    print(f"[UPSTREAM DATA DEBUG] Total upstream edges: {len(upstream_edges)}")
    print(f"[UPSTREAM DATA DEBUG] Data edges: {len(data_edges)}")
    for edge in data_edges:
        print(f"  - Source: {edge.get('source')}, targetHandle: {edge.get('targetHandle')}")
    print(f"[UPSTREAM DATA DEBUG] Context edges: {len(context_edges)}")
    for edge in context_edges:
        print(f"  - Source: {edge.get('source')}, targetHandle: {edge.get('targetHandle')}")
    print(f"{'='*80}\n")

    # Execute data sources (these are iterated over)
    data_results = []
    for edge in data_edges:
        source_node_id = edge.get('source')  # Now a backend ID

        if not source_node_id:
            continue

        try:
            source_node = WorkflowNode.objects.get(
                id=source_node_id,
                workflow=workflow,
                is_active=True
            )

            source_instance = NodeFactory.create_node(
                node_id=source_node.id,
                node_type=source_node.node_type,
                configuration=source_node.configuration,
                workflow_id=workflow.id,
                execution_id=0,
                position=source_node.position
            )

            source_results = source_instance.run()
            if source_results:
                data_results.extend(source_results)
                print(f"[DATA SOURCE DEBUG] Source node {source_node_id} returned {len(source_results)} rows")
                if source_results:
                    print(f"[DATA SOURCE DEBUG] Sample row keys: {list(source_results[0].keys())}")

        except (WorkflowNode.DoesNotExist, Exception) as e:
            print(f"ERROR: Failed to execute data source {source_node_id}: {e}")
            continue

    # Execute context sources (these are broadcast to all data rows)
    context_data = {}
    for edge in context_edges:
        source_node_id = edge.get('source')  # Now a backend ID

        if not source_node_id:
            continue

        try:
            source_node = WorkflowNode.objects.get(
                id=source_node_id,
                workflow=workflow,
                is_active=True
            )

            source_instance = NodeFactory.create_node(
                node_id=source_node.id,
                node_type=source_node.node_type,
                configuration=source_node.configuration,
                workflow_id=workflow.id,
                execution_id=0,
                position=source_node.position
            )

            source_results = source_instance.run()
            if source_results and len(source_results) > 0:
                # Merge first row from context source into context_data
                context_data.update(source_results[0])
                print(f"[CONTEXT SOURCE DEBUG] Source node {source_node_id} returned {len(source_results)} rows")
                print(f"[CONTEXT SOURCE DEBUG] Context row: {source_results[0]}")
                print(f"[CONTEXT SOURCE DEBUG] Updated context_data: {context_data}")

        except (WorkflowNode.DoesNotExist, Exception) as e:
            print(f"ERROR: Failed to execute context source {source_node_id}: {e}")
            continue

    # Return structured data if we have context edges, otherwise backward compatible
    if context_edges:
        result = {
            'data': data_results,
            'context': context_data
        }
        print(f"\n[FINAL RETURN DEBUG] Returning structured data:")
        print(f"  - data rows: {len(result['data'])}")
        print(f"  - context keys: {list(result['context'].keys())}")
        print(f"  - context values sample: {str(result['context'])[:200]}")
        print(f"{'='*80}\n")
        return result
    else:
        # Backward compatibility: return data results directly
        print(f"\n[FINAL RETURN DEBUG] Returning backward-compatible list ({len(data_results) if data_results else 0} rows)\n")
        return data_results if data_results else None


def _update_chat_conversation_with_response(execution: WorkflowExecution, node_results: dict):
    """
    Update WorkflowChatConversation with bot response extracted from workflow results.

    This function is called after a chat-triggered workflow completes successfully.
    It extracts the final output from the workflow and saves it back to the conversation.

    Args:
        execution: WorkflowExecution instance (must have triggered_by='chat')
        node_results: Dictionary of {node_id: results} from workflow execution

    Workflow structure for chat:
        trigger_chat -> agent (with toolbox) -> [optional output node]

    The bot response is extracted from:
        1. Output node (if present) - final formatted output
        2. Agent node (if no output) - agent's response directly
        3. Last non-trigger node as fallback
    """
    from workflows.models import WorkflowChatConversation

    try:
        # Find the conversation for this execution
        conversation = WorkflowChatConversation.objects.get(
            workflow_execution=execution
        )

        print(f"\n[CHAT RESPONSE] Extracting bot response for conversation {conversation.id}")
        print(f"[CHAT RESPONSE] Node results available: {list(node_results.keys())}")

        # Extract bot response from results
        bot_response = _extract_bot_response(node_results, execution)

        # Update conversation with response
        conversation.response_data = {
            'bot_response': bot_response,
            'execution_id': execution.id,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'node_count': len(node_results)
        }
        conversation.status = 'completed'
        conversation.save()

        print(f"[CHAT RESPONSE] Successfully saved bot response to conversation")
        print(f"[CHAT RESPONSE] Response preview: {str(bot_response)[:200]}")

    except WorkflowChatConversation.DoesNotExist:
        print(f"[CHAT RESPONSE] ERROR: No conversation found for execution {execution.id}")
    except Exception as e:
        import traceback
        print(f"[CHAT RESPONSE] ERROR: Failed to update conversation: {str(e)}")
        traceback.print_exc()


def _extract_bot_response(node_results: dict, execution: WorkflowExecution) -> str:
    """
    Extract bot response from workflow node results.

    Extraction strategy:
    1. Look for output node - if present, use its formatted output
    2. Look for agent node - extract response based on agent type:
       - Unstructured: 'agent_response' field
       - Structured: JSON output fields
    3. Fallback to last non-trigger node results

    Args:
        node_results: Dictionary of {node_id: results}
        execution: WorkflowExecution instance for context

    Returns:
        str: Formatted bot response for display in chat
    """
    from workflows.models import WorkflowNode

    if not node_results:
        return "Workflow completed with no output."

    # Get all nodes to identify their types
    nodes = WorkflowNode.objects.filter(
        workflow=execution.workflow,
        is_active=True
    )

    # Create mapping of node_id -> node_type
    node_type_map = {node.id: node.node_type for node in nodes}

    # Strategy 1: Look for output node
    output_nodes = [
        (node_id, results)
        for node_id, results in node_results.items()
        if node_type_map.get(node_id) == 'output'
    ]

    if output_nodes:
        output_node_id, output_results = output_nodes[0]
        print(f"[EXTRACT RESPONSE] Found output node {output_node_id}")
        # Output node typically saves data and returns success message
        # We'll use the actual saved data or a confirmation message
        if isinstance(output_results, dict):
            return output_results.get('message', str(output_results))
        return str(output_results)

    # Strategy 2: Look for agent node
    agent_nodes = [
        (node_id, results)
        for node_id, results in node_results.items()
        if node_type_map.get(node_id) == 'agent'
    ]

    if agent_nodes:
        agent_node_id, agent_results = agent_nodes[0]
        print(f"[EXTRACT RESPONSE] Found agent node {agent_node_id}")

        # Agent results are typically a list of processed records
        if isinstance(agent_results, list) and len(agent_results) > 0:
            first_result = agent_results[0]

            # Check for unstructured agent response
            if 'agent_response' in first_result:
                response = first_result['agent_response']
                print(f"[EXTRACT RESPONSE] Extracted unstructured agent response")
                return response

            # Check for structured agent response (multiple fields)
            # Exclude metadata and original input fields
            exclude_keys = ['_agent_metadata', '_trigger', 'user_input', 'session_id', 'timestamp']
            response_fields = {
                k: v for k, v in first_result.items()
                if k not in exclude_keys
            }

            if response_fields:
                print(f"[EXTRACT RESPONSE] Extracted structured agent response with fields: {list(response_fields.keys())}")
                # Format structured response nicely
                import json
                return json.dumps(response_fields, indent=2)

        # If agent results are not in expected format, return as string
        return str(agent_results)

    # Strategy 3: Fallback - use last non-trigger node
    trigger_types = ['trigger_manual', 'trigger_schedule', 'trigger_chat']
    non_trigger_results = [
        (node_id, results)
        for node_id, results in node_results.items()
        if node_type_map.get(node_id) not in trigger_types
    ]

    if non_trigger_results:
        last_node_id, last_results = non_trigger_results[-1]
        print(f"[EXTRACT RESPONSE] Using fallback - last non-trigger node {last_node_id}")

        if isinstance(last_results, dict):
            import json
            return json.dumps(last_results, indent=2)
        elif isinstance(last_results, list):
            import json
            return json.dumps(last_results, indent=2)
        return str(last_results)

    # Final fallback
    return "Workflow completed successfully."
