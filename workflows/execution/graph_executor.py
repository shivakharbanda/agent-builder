"""
Pydantic AI Graph Executor

Executes workflows using Pydantic AI Graph and updates Django models.
"""

import asyncio
from django.utils import timezone
from workflows.models import WorkflowExecution
from workflows.execution.graph_builder import WorkflowGraphBuilder
from workflows.execution.state import WorkflowState


async def execute_workflow_with_graph(execution_id: int):
    """
    Execute workflow using Pydantic AI Graph.

    This is the main entry point for graph-based workflow execution.
    It builds the graph, runs it, and updates Django models with results.

    Args:
        execution_id: ID of WorkflowExecution record

    Returns:
        WorkflowState: Final state after execution

    Raises:
        Exception: Any errors during execution
    """
    try:
        print(f"\n{'='*80}")
        print(f"[GRAPH EXECUTOR] Starting execution {execution_id}")
        print(f"{'='*80}\n")

        # Get execution record with related workflow (async ORM with select_related)
        execution = await WorkflowExecution.objects.select_related('workflow').aget(id=execution_id)
        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.progress_message = 'Building workflow graph...'
        execution.progress_percentage = 10.0
        await execution.asave()

        # Build graph (workflow is already loaded via select_related)
        print(f"[GRAPH EXECUTOR] Building graph for workflow {execution.workflow.id}")
        builder = WorkflowGraphBuilder(
            workflow=execution.workflow,
            execution_id=execution_id
        )
        graph = builder.build()

        # Get starting node
        start_node = builder.get_start_node()
        if not start_node:
            raise Exception("No start node found in workflow")

        # Initialize state
        print(f"[GRAPH EXECUTOR] Initializing workflow state")
        state = WorkflowState(
            workflow_id=execution.workflow.id,
            execution_id=execution_id
        )

        # Update progress
        execution.progress_message = f'Starting from {start_node.node_type} node...'
        execution.progress_percentage = 20.0
        await execution.asave()

        # Execute graph
        print(f"\n[GRAPH EXECUTOR] Executing graph from node {start_node.node_id} ({start_node.node_type})")
        print(f"{'='*80}\n")

        result = await graph.run(start_node, state=state)

        print(f"\n{'='*80}")
        print(f"[GRAPH EXECUTOR] Graph execution completed")
        print(f"{'='*80}\n")

        # Update execution record with success
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.progress_percentage = 100.0
        execution.progress_message = 'Workflow completed successfully'

        # Dump state excluding message_history which contains non-serializable ModelMessage objects
        state_dict = result.state.model_dump(mode='json')
        # Clean message_history from current_data if present
        if isinstance(state_dict.get('current_data'), list):
            for item in state_dict['current_data']:
                if isinstance(item, dict) and 'message_history' in item:
                    item['message_history'] = f"<{len(item['message_history'])} messages>"
        elif isinstance(state_dict.get('current_data'), dict) and 'message_history' in state_dict['current_data']:
            msg_count = len(state_dict['current_data']['message_history'])
            state_dict['current_data']['message_history'] = f"<{msg_count} messages>"

        execution.execution_log = {
            'state': state_dict,
            'execution_order': result.state.node_execution_order,
            'node_count': len(result.state.node_results),
            'final_data_size': len(result.state.current_data) if isinstance(result.state.current_data, list) else 1
        }
        await execution.asave()

        # If this was a chat-triggered workflow, update conversation with response
        if execution.triggered_by == 'chat':
            await _update_chat_conversation_with_response(execution, result.state)

        print(f"[GRAPH EXECUTOR] Execution {execution_id} completed successfully")
        print(f"[GRAPH EXECUTOR] Executed {len(result.state.node_execution_order)} nodes")
        print(f"[GRAPH EXECUTOR] Execution order: {result.state.node_execution_order}")

        return result.state

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        print(f"\n[GRAPH EXECUTOR] ERROR: Execution {execution_id} failed")
        print(f"[GRAPH EXECUTOR] Error: {str(e)}")
        print(error_details)

        # Update execution record with failure
        try:
            execution = await WorkflowExecution.objects.aget(id=execution_id)
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.execution_log = {
                'error': str(e),
                'error_details': error_details
            }
            execution.completed_at = timezone.now()
            await execution.asave()
        except Exception as save_error:
            print(f"[GRAPH EXECUTOR] Failed to update execution record: {save_error}")

        raise


def execute_workflow_sync(execution_id: int):
    """
    Synchronous wrapper for graph execution.

    Used for background thread execution.

    Args:
        execution_id: ID of WorkflowExecution

    Returns:
        WorkflowState: Final state
    """
    return asyncio.run(execute_workflow_with_graph(execution_id))


async def _update_chat_conversation_with_response(execution: WorkflowExecution, state: WorkflowState):
    """
    Update chat conversation with bot response from workflow results.

    Args:
        execution: WorkflowExecution instance
        state: Final workflow state
    """
    from workflows.models import WorkflowChatConversation

    try:
        # Find conversation for this execution (async ORM)
        conversation = await WorkflowChatConversation.objects.aget(
            workflow_execution=execution
        )

        print(f"\n[CHAT RESPONSE] Extracting bot response for conversation {conversation.id}")

        # Extract bot response from state
        bot_response = _extract_bot_response(state)

        # Extract new_messages_json from state (from agent node result)
        new_messages_json = ''
        final_data = state.current_data
        if isinstance(final_data, list) and len(final_data) > 0:
            final_data = final_data[0]
        if isinstance(final_data, dict):
            new_messages_json = final_data.get('new_messages_json', '')
            # Decode bytes to string if needed (result.new_messages_json() returns bytes)
            if isinstance(new_messages_json, bytes):
                new_messages_json = new_messages_json.decode('utf-8')

        # Update conversation
        conversation.response_data = {
            'bot_response': bot_response,
            'execution_id': execution.id,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'node_count': len(state.node_results)
        }
        conversation.message_history_blob = new_messages_json  # Store message history blob
        conversation.status = 'completed'
        await conversation.asave()

        print(f"[CHAT RESPONSE] Bot response saved: {bot_response[:200]}...")
        print(f"[CHAT RESPONSE] Message history blob saved: {len(new_messages_json)} chars")

    except WorkflowChatConversation.DoesNotExist:
        print(f"[CHAT RESPONSE] No conversation found for execution {execution.id}")
    except Exception as e:
        import traceback
        print(f"[CHAT RESPONSE] Error updating conversation: {e}")
        traceback.print_exc()


def _extract_bot_response(state: WorkflowState) -> str:
    """
    Extract bot response from workflow state.

    Strategy:
    1. Look for agent node response (last agent in execution order)
    2. Format based on agent type (structured/unstructured)
    3. Handle agent execution errors gracefully

    Args:
        state: Final workflow state

    Returns:
        str: Bot response text or error message
    """
    if not state.current_data:
        return "Workflow completed with no output."

    # Get current data (final output)
    final_data = state.current_data

    # If it's a list, take first item
    if isinstance(final_data, list) and len(final_data) > 0:
        final_data = final_data[0]

    if not isinstance(final_data, dict):
        return str(final_data)

    # Check for agent execution errors first
    agent_metadata = final_data.get('_agent_metadata', {})
    if agent_metadata and not agent_metadata.get('success', True):
        error_msg = agent_metadata.get('error', 'Unknown error occurred')
        return f"Sorry, I encountered an error: {error_msg}"

    # Check for agent response (unstructured)
    if 'agent_response' in final_data:
        return final_data['agent_response']

    # Check for structured agent output (exclude metadata and trigger fields)
    exclude_keys = ['_agent_metadata', '_trigger', 'user_input', 'session_id', 'timestamp', 'message_history', 'new_messages_json']
    response_fields = {
        k: v for k, v in final_data.items()
        if k not in exclude_keys and not k.startswith('_')
    }

    if response_fields:
        # Format structured response nicely
        import json
        return json.dumps(response_fields, indent=2)

    # Fallback
    return "Workflow completed successfully."
