import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import type { Route } from './+types/create';

import { Layout } from '../../components/layout/Layout';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { WorkflowCanvas, type WorkflowCanvasRef } from '../../components/workflow/WorkflowCanvas';
import type { WorkflowConfig } from '../../components/workflow/types';
import { NodePalette } from '../../components/workflow/NodePalette';
import { ChatInterface } from '../../components/workflow/ChatInterface';
import { ConfigViewer } from '../../components/workflow/ConfigViewer';
import { ExecutionResultModal } from '../../components/workflow/ExecutionResultModal';
import { WorkflowErrorBoundary } from '../../components/ui/ErrorBoundary';
import { useFormSubmit } from '../../hooks/useAPI';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/useToast';
import { ToastContainer } from '../../components/ui/Toast';
import { validateWorkflowConfig } from '../../lib/workflowConfigValidator';
import { useExecutionPolling } from '../../hooks/useExecutionPolling';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Create Workflow - Agent Builder" },
    { name: "description", content: "Build AI workflows with visual node editor" },
  ];
}

export default function CreateWorkflow() {
  const navigate = useNavigate();
  const params = useParams();
  const isEditMode = Boolean(params.id);
  const projectId = params.projectId ? parseInt(params.projectId) : undefined;
  const [searchValue, setSearchValue] = useState('');
  const [activeTab, setActiveTab] = useState<'manual' | 'chat'>('manual');
  const [workflowName, setWorkflowName] = useState('Untitled Workflow');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [savedWorkflowId, setSavedWorkflowId] = useState<number | null>(params.id ? parseInt(params.id) : null);
  const [workflowConfig, setWorkflowConfig] = useState<WorkflowConfig>({
    nodes: [],
    edges: [],
    properties: {
      watermark_start_date: '',
      watermark_end_date: '',
      schedule: '',
      timeout: 3600,
      retry_count: 3,
      notification_email: ''
    },
    metadata: {
      name: 'Untitled Workflow',
      description: '',
      version: '1.0.0',
      created: new Date().toISOString(),
      updated: new Date().toISOString(),
    }
  });
  const [showConfig, setShowConfig] = useState(false);
  const [isLoadingWorkflow, setIsLoadingWorkflow] = useState(isEditMode);
  const [showSuccessToast, setShowSuccessToast] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [canvasKey, setCanvasKey] = useState(0);
  const { toasts, showToast, removeToast } = useToast();
  const { pollExecution } = useExecutionPolling();

  // Execution state
  const [executionState, setExecutionState] = useState<{
    isExecuting: boolean;
    results: any;
    error: string | null;
    showModal: boolean;
  }>({
    isExecuting: false,
    results: null,
    error: null,
    showModal: false,
  });

  // Node execution results cache (for input mapping)
  const [nodeExecutionCache, setNodeExecutionCache] = useState<Record<string, any>>({});

  // Canvas ref for imperative API (AI workflow builder)
  const canvasRef = useRef<WorkflowCanvasRef>(null);

  // Form submission hook - use different API based on mode
  const { loading: saving, error: saveError, submit: submitWorkflow } = useFormSubmit(
    async (data: any) => {
      if (isEditMode) {
        return api.updateCompleteWorkflow(Number(params.id), data);
      } else {
        return api.saveCompleteWorkflow(data);
      }
    }
  );

  // Fetch workflow details if editing
  useEffect(() => {
    const workflowId = params.id;
    if (workflowId) {
      api.getWorkflow(Number(workflowId))
        .then(workflow => {
          console.log('Workflow details:', workflow);

          setIsLoadingWorkflow(true);

          // Map workflow data back to state
          setWorkflowName(workflow.name);
          setWorkflowDescription(workflow.description);

          // Backend configuration now has backend IDs directly - use as-is
          setWorkflowConfig({
            nodes: workflow.configuration.nodes,  // Already has backend IDs
            edges: workflow.configuration.edges,  // Already has backend IDs
            metadata: workflow.configuration.metadata,
            properties: workflow.properties
          });

          // Brief delay to prevent recursive updates
          setTimeout(() => setIsLoadingWorkflow(false), 100);
        })
        .catch(error => {
          console.error('Error fetching workflow:', error);
        });
    }
  }, [params.id]);

  const handleConfigChange = (config: WorkflowConfig) => {
    if (isLoadingWorkflow) return; // Skip during initial load
    setWorkflowConfig(config);
    setHasUnsavedChanges(true);
  };

  const handleChatCommand = (command: string) => {
    // Handle chat commands here
    // You can extend this to parse commands and manipulate the workflow
  };

  // NEW: AI Workflow Config Handler
  const handleWorkflowConfigComplete = (config: any) => {
    console.log('AI Workflow Config:', config);

    // Validate workflow structure
    const validationResult = validateWorkflowConfig(config);

    if (!validationResult.isValid) {
      console.error('Workflow validation failed:', validationResult.errors);
      showToast(`Configuration validation failed: ${validationResult.errors.join(', ')}`, 'error');
      return;
    }

    const validatedConfig = validationResult.config!;

    // Update config
    setWorkflowConfig({
      nodes: validatedConfig.nodes,
      edges: validatedConfig.edges,
      properties: validatedConfig.properties || workflowConfig.properties,
      metadata: {
        name: validatedConfig.name,
        description: validatedConfig.description,
        version: '1.0.0',
        created: new Date().toISOString(),
        updated: new Date().toISOString(),
      }
    });

    setWorkflowName(validatedConfig.name);
    setWorkflowDescription(validatedConfig.description);

    // Force canvas remount to initialize with AI config
    setCanvasKey(prev => prev + 1);

    // Auto-switch to Manual tab to show the created workflow
    setActiveTab('manual');

    showToast('✨ Workflow structure created! Configure node details and save.', 'success');
  };

  // AI Action Handler - Applies AI actions directly to canvas via imperative API
  const handleAIAction = (structuredResponse: any) => {
    if (!canvasRef.current) {
      console.warn('[create.tsx] Canvas ref not available, skipping AI action');
      return;
    }

    console.log('[create.tsx] Handling AI action:', structuredResponse);

    try {
      switch (structuredResponse.action_type) {
        case 'node_add':
          const nodeData = structuredResponse.data;
          const nodeId = canvasRef.current.addNode({
            node_id: nodeData.node_id,  // Pass AI's node_id to canvas
            node_type: nodeData.node_type,
            position: nodeData.position,
            config: nodeData.config,
            connects_to: nodeData.connects_to,
            label: nodeData.label
          });
          console.log('[create.tsx] Added node via canvas API:', nodeId);
          break;

        case 'edge_add':
          const edgeData = structuredResponse.data;
          canvasRef.current.addEdge({
            source: edgeData.source_node_id,
            target: edgeData.target_node_id,
            source_handle: edgeData.source_handle,
            target_handle: edgeData.target_handle
          });
          console.log('[create.tsx] Added edge via canvas API:', `${edgeData.source_node_id} → ${edgeData.target_node_id}`);
          break;

        case 'node_edit':
        case 'node_update':
          const editData = structuredResponse.data;
          canvasRef.current.updateNode(editData.node_id, {
            config: editData.config_updates,
            position: editData.position_update
          });
          console.log('[create.tsx] Updated node via canvas API:', editData.node_id);
          break;

        case 'node_remove':
          const removeData = structuredResponse.data;
          canvasRef.current.removeNode(removeData.node_id);
          console.log('[create.tsx] Removed node via canvas API:', removeData.node_id);
          break;

        case 'edge_remove':
          const edgeRemoveData = structuredResponse.data;
          console.log('[create.tsx] Edge remove action received');
          console.log('[create.tsx] Edge ID to remove:', edgeRemoveData.edge_id);
          console.log('[create.tsx] Canvas ref exists:', !!canvasRef.current);

          if (canvasRef.current) {
            console.log('[create.tsx] Calling removeEdge on canvas...');
            canvasRef.current.removeEdge(edgeRemoveData.edge_id);
            console.log('[create.tsx] removeEdge called successfully');
          } else {
            console.error('[create.tsx] Canvas ref is null! Cannot remove edge');
          }
          break;

        case 'conversation':
          // Just a message, no canvas action needed
          console.log('[create.tsx] AI conversation message:', structuredResponse.data.message);
          break;

        case 'workflow_complete':
          console.log('[create.tsx] Workflow building complete:', structuredResponse.data.summary);
          showToast('Workflow complete! You can now save it.', 'success');
          break;

        default:
          console.warn('[create.tsx] Unknown AI action type:', structuredResponse.action_type);
      }
    } catch (error) {
      console.error('[create.tsx] Error handling AI action:', error);
      showToast('Error applying AI action', 'error');
    }
  };

  const handleSaveWorkflow = async () => {
    try {
      // Validate workflow before saving
      if (!workflowName.trim()) {
        alert('Please enter a workflow name');
        return;
      }

      if (workflowConfig.nodes.length === 0) {
        alert('Please add at least one node to your workflow before saving');
        return;
      }

      // Prepare workflow data based on mode
      const workflowData = isEditMode ? {
        // Update API expects simpler structure
        name: workflowName,
        description: workflowDescription,
        configuration: {
          nodes: workflowConfig.nodes,
          edges: workflowConfig.edges,
          metadata: {
            ...workflowConfig.metadata,
            name: workflowName,
            description: workflowDescription,
            updated: new Date().toISOString()
          }
        }
      } : {
        // Create API expects full structure
        name: workflowName,
        description: workflowDescription,
        project: 1, // TODO: Get from context or user selection
        configuration: {
          nodes: workflowConfig.nodes,
          edges: workflowConfig.edges,
          metadata: {
            ...workflowConfig.metadata,
            name: workflowName,
            description: workflowDescription,
            updated: new Date().toISOString()
          }
        },
        properties: workflowConfig.properties
      };

      // API call (create or update)
      const savedWorkflow = await submitWorkflow(workflowData);

      // Backend now returns configuration with backend IDs - update local state
      if (savedWorkflow.configuration) {
        setWorkflowConfig({
          nodes: savedWorkflow.configuration.nodes,
          edges: savedWorkflow.configuration.edges,
          metadata: savedWorkflow.configuration.metadata,
          properties: savedWorkflow.properties || workflowConfig.properties
        });
      }

      // Reset unsaved changes flag after successful save
      setHasUnsavedChanges(false);

      // Update saved workflow ID
      setSavedWorkflowId(savedWorkflow.id);

      // Navigate based on mode
      if (isEditMode) {
        // Stay on edit page - show success toast
        setShowSuccessToast(true);
        setTimeout(() => setShowSuccessToast(false), 3000);
      } else {
        // Go to edit page after create so user can continue building
        navigate(`/workflows/${savedWorkflow.id}/edit`);
      }
    } catch (error) {
      // Error is handled by useFormSubmit hook and displayed in UI
    }
  };

  const handleExecuteWorkflow = async () => {
    if (!isEditMode) {
      showToast('Please save the workflow before executing', 'warning');
      return;
    }
    if (hasUnsavedChanges) {
      showToast('Please save your changes before executing', 'warning');
      return;
    }
    try {
      const result = await api.executeWorkflow(Number(params.id));
      showToast('Workflow execution started', 'success');
      console.log('Execution result:', result);
    } catch (error) {
      showToast('Failed to execute workflow', 'error');
      console.error('Execution error:', error);
    }
  };

  const handleExecuteNode = async (nodeId: string, nodeType?: string, nodeData?: any) => {
    const workflowId = params.id;

    // Check if workflow has been saved at least once
    if (!workflowId) {
      showToast('Please save the workflow before executing nodes', 'warning');
      return;
    }

    // Warn about unsaved changes but don't block execution
    // (Execution will use the last saved node configuration)
    if (hasUnsavedChanges) {
      console.warn('Executing with unsaved changes - using last saved configuration');
    }

    // Extract backend ID from nodeData (nodeId from React Flow is a string)
    const backendNodeId = nodeData?.backendId || nodeId;

    console.log('DEBUG: Executing node with:', {
      workflowId,
      nodeId,
      backendNodeId,
      nodeData
    });

    // Show executing state
    setExecutionState({
      isExecuting: true,
      results: null,
      error: null,
      showModal: true,
    });

    try {
      // Start async execution using backend ID
      const { execution_id } = await api.executeWorkflow(Number(workflowId), Number(backendNodeId));

      console.log('[CreateWorkflow] Execution started:', execution_id);

      // Poll for results
      await pollExecution(execution_id, {
        onProgress: (status, progressPercentage, progressMessage) => {
          console.log('[CreateWorkflow] Progress:', { status, progressPercentage, progressMessage });
          setExecutionState(prev => ({
            ...prev,
            results: {
              ...prev.results,
              status,
              progress_percentage: progressPercentage,
              progress_message: progressMessage
            }
          }));
        },
        onComplete: (executionResult) => {
          console.log('[CreateWorkflow] Completed:', executionResult);

          // Cache the results by frontend node ID (for input mapping dropdown)
          setNodeExecutionCache(prev => ({
            ...prev,
            [nodeId]: executionResult.results
          }));

          // Show results in modal
          setExecutionState({
            isExecuting: false,
            results: executionResult,
            error: null,
            showModal: true,
          });

          showToast('Node executed successfully', 'success');
        },
        onError: (error) => {
          console.error('[CreateWorkflow] Execution error:', error);

          setExecutionState({
            isExecuting: false,
            results: null,
            error: error,
            showModal: true,
          });

          showToast('Node execution failed', 'error');
        }
      });

    } catch (error: any) {
      // Handle initial request error
      console.error('[CreateWorkflow] Failed to start execution:', error);

      setExecutionState({
        isExecuting: false,
        results: error.response?.data || null,
        error: error.response?.data?.error || error.message || 'Failed to start execution',
        showModal: true,
      });

      showToast('Failed to start execution', 'error');
    }
  };

  return (
    <Layout fullHeight={true}>
      <div className="flex flex-col min-h-[calc(100vh-80px)] h-[calc(100vh-80px)]">
        {/* Header */}
        <div className="px-4 sm:px-6 lg:px-8 py-4 border-b border-[#374151] bg-[#1a2633]">
          <div className="flex items-center justify-between">
            <div className="flex-1 max-w-2xl">
              <div className="flex items-center gap-4 mb-3">
                <Input
                  type="text"
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  className="text-2xl font-bold bg-transparent border-none focus:ring-1 focus:ring-[#1173d4] text-white placeholder-gray-500 p-0 h-auto"
                  placeholder="Enter workflow name..."
                />
              </div>
              <div className="flex items-center gap-4">
                <Input
                  type="text"
                  value={workflowDescription}
                  onChange={(e) => setWorkflowDescription(e.target.value)}
                  className="bg-transparent border-none focus:ring-1 focus:ring-[#1173d4] text-gray-400 placeholder-gray-500 p-0 h-auto text-sm"
                  placeholder="Add a description for your workflow..."
                />
                {workflowConfig.nodes.length > 0 && (
                  <span className="text-sm text-gray-500 whitespace-nowrap">
                    • {workflowConfig.nodes.length} nodes, {workflowConfig.edges.length} connections
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {saveError && (
                <div className="text-red-400 text-sm mr-2">
                  Save failed: {saveError}
                </div>
              )}
              <Button variant="outline" asChild disabled={saving}>
                <Link to="/workflows">Cancel</Link>
              </Button>
              {isEditMode && (
                <Button
                  variant="outline"
                  onClick={handleExecuteWorkflow}
                  disabled={saving}
                  leftIcon={<span className="material-symbols-outlined text-base">play_arrow</span>}
                >
                  Execute Workflow
                </Button>
              )}
              <Button onClick={handleSaveWorkflow} disabled={saving}>
                {saving ? (
                  <>
                    <span className="material-symbols-outlined text-sm mr-1 animate-spin">progress_activity</span>
                    {isEditMode ? 'Updating...' : 'Saving...'}
                  </>
                ) : (
                  isEditMode ? 'Update Workflow' : 'Save Workflow'
                )}
              </Button>
            </div>
          </div>
        </div>

        <div className="flex-grow flex overflow-hidden relative">
          {/* Sidebar */}
          <aside className="w-80 sm:w-96 flex flex-col border-r border-[#374151] bg-[#1a2633] z-10">
            {/* Tab Switcher */}
            <div className="border-b border-[#374151]">
              <div className="flex">
                <button
                  onClick={() => setActiveTab('manual')}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                    activeTab === 'manual'
                      ? 'bg-[#111a22] text-[#1173d4] border-b-2 border-[#1173d4]'
                      : 'text-gray-400 hover:text-white hover:bg-[#111a22]/50'
                  }`}
                >
                  <span className="material-symbols-outlined text-base">widgets</span>
                  Manual
                </button>
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                    activeTab === 'chat'
                      ? 'bg-[#111a22] text-[#1173d4] border-b-2 border-[#1173d4]'
                      : 'text-gray-400 hover:text-white hover:bg-[#111a22]/50'
                  }`}
                >
                  <span className="material-symbols-outlined text-base">smart_toy</span>
                  AI Chat
                </button>
              </div>
            </div>

            {/* Tab Content */}
            {activeTab === 'manual' ? (
              <>
                {/* Search */}
                <div className="p-4 border-b border-[#374151]">
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                      search
                    </span>
                    <Input
                      type="text"
                      placeholder="Search nodes..."
                      value={searchValue}
                      onChange={(e) => setSearchValue(e.target.value)}
                      className="w-full bg-[#111a22] border border-[#374151] rounded-md pl-10 pr-4 py-2 focus:ring-[#1173d4] focus:border-[#1173d4] text-sm text-white"
                    />
                  </div>
                </div>

                {/* Node Palette */}
                <div className="flex-grow overflow-y-auto p-4">
                  <NodePalette />
                </div>
              </>
            ) : (
              /* Chat Interface - Full Height */
              <div className="flex-grow flex flex-col overflow-hidden">
                <ChatInterface
                  onCommand={handleChatCommand}
                  onWorkflowConfigComplete={handleWorkflowConfigComplete}
                  onAIAction={handleAIAction}
                  projectId={projectId || 1}
                />
              </div>
            )}
          </aside>

          {/* Main Canvas */}
          <main className="flex-grow bg-[#111a22] relative">
            <WorkflowErrorBoundary>
              <WorkflowCanvas
                ref={canvasRef}
                key={canvasKey}
                onConfigChange={handleConfigChange}
                initialConfig={workflowConfig}
                isLoading={isLoadingWorkflow}
                onExecuteNode={handleExecuteNode}
                nodeExecutionCache={nodeExecutionCache}
                workflowId={savedWorkflowId}
              />
            </WorkflowErrorBoundary>
          </main>

          {/* Config Viewer */}
          <ConfigViewer
            config={workflowConfig}
            isVisible={showConfig}
            onToggle={() => setShowConfig(!showConfig)}
          />
        </div>
      </div>

      {/* Success Toast */}
      {showSuccessToast && (
        <div className="fixed top-4 right-4 z-50">
          <div className="bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-3 animate-in slide-in-from-right">
            <span className="material-symbols-outlined text-xl">check_circle</span>
            <span className="font-medium">Workflow updated successfully!</span>
            <button
              onClick={() => setShowSuccessToast(false)}
              className="ml-2 text-green-100 hover:text-white transition-colors"
            >
              <span className="material-symbols-outlined text-sm">close</span>
            </button>
          </div>
        </div>
      )}

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />

      {/* Execution Result Modal */}
      <ExecutionResultModal
        isOpen={executionState.showModal}
        onClose={() => setExecutionState({ ...executionState, showModal: false })}
        results={executionState.results}
        error={executionState.error}
        isExecuting={executionState.isExecuting}
      />
    </Layout>
  );
}