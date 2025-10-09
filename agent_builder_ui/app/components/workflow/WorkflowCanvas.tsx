import { useCallback, useState, useEffect, useRef } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { WorkflowConfig } from './types';
import { NodeConfigModal } from './NodeConfigModal';
import { WorkflowPropertiesModal } from './WorkflowPropertiesModal';
import { WorkflowTriggerChat } from './WorkflowTriggerChat';
import { Button } from '../ui/Button';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/useToast';
import { ToastContainer } from '../ui/Toast';
import { TriggerManualNode, TriggerScheduleNode, TriggerChatNode, DatabaseNode, AgentNode, OutputNode, FilterNode, ScriptNode, ConditionalNode  } from './Nodes'
interface WorkflowCanvasProps {
  onConfigChange?: (config: WorkflowConfig) => void;
  initialConfig?: WorkflowConfig;
  isLoading?: boolean;
  onExecuteNode?: (nodeId: string) => void;
  nodeExecutionCache?: Record<string, any>;
  workflowId?: number | null;
}



const nodeTypes = {
  // Trigger nodes
  trigger_manual: TriggerManualNode,
  trigger_schedule: TriggerScheduleNode,
  trigger_chat: TriggerChatNode,
  // Data nodes
  database: DatabaseNode,
  agent: AgentNode,
  output: OutputNode,
  filter: FilterNode,
  script: ScriptNode,
  conditional: ConditionalNode,
};

export function WorkflowCanvas({ onConfigChange, initialConfig, isLoading, onExecuteNode, nodeExecutionCache, workflowId }: WorkflowCanvasProps) {
  // React Flow manages node/edge arrays internally
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Toast notifications
  const { toasts, showToast, removeToast } = useToast();

  // Chat state
  const [chatOpen, setChatOpen] = useState(false);
  const [chatWelcomeMessage, setChatWelcomeMessage] = useState<string>('');

  // Node configuration modal state
  const [configModal, setConfigModal] = useState<{
    isOpen: boolean;
    nodeId: string | null;
    nodeType: string | null;
    nodeData: any | null;
    edges: any[];
    nodes: any[];
    executionCache: Record<string, any>;
  }>({
    isOpen: false,
    nodeId: null,
    nodeType: null,
    nodeData: null,
    edges: [],
    nodes: [],
    executionCache: {},
  });

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

  // Workflow properties modal state
  const [propertiesModal, setPropertiesModal] = useState({
    isOpen: false
  });

  // Trigger execution handlers (defined before useEffect to avoid initialization errors)
  const handleExecuteTrigger = useCallback(async (triggerWorkflowId: number) => {
    try {
      const result = await api.executeWorkflow(triggerWorkflowId);
      showToast(`Workflow execution started (ID: ${result.execution_id})`, 'success');
    } catch (error: any) {
      showToast(error.detail || 'Failed to execute workflow', 'error');
    }
  }, [showToast]);

  const handleOpenChat = useCallback((welcomeMsg?: string) => {
    setChatWelcomeMessage(welcomeMsg || 'Hi! Send me a message to start the workflow.');
    setChatOpen(true);
  }, []);

  const handleCloseChat = useCallback(() => {
    setChatOpen(false);
  }, []);

  // Node configuration handlers (defined before useEffect to avoid initialization errors)
  const handleNodeConfig = useCallback((nodeId: string, nodeType: string, nodeData: any) => {
    setConfigModal({
      isOpen: true,
      nodeId,
      nodeType,
      nodeData,
      edges: edges,
      nodes: nodes,
      executionCache: nodeExecutionCache || {},
    });
  }, [edges, nodes, nodeExecutionCache]);

  const handleNodeDelete = useCallback((nodeId: string) => {
    setNodes((nodes) => nodes.filter((node) => node.id !== nodeId));
    setEdges((edges) => edges.filter((edge) =>
      edge.source !== nodeId && edge.target !== nodeId
    ));
  }, [setNodes, setEdges]);

  // Simple one-time initialization
  const [initialized, setInitialized] = useState(false);
  const [hasInitialized, setHasInitialized] = useState(false);
  const lastConfigRef = useRef<WorkflowConfig | null>(null);

  useEffect(() => {
    if (hasInitialized) return; // Initialize only once
    if (isLoading) return; // Wait for API data in edit mode

    setHasInitialized(true);
    lastConfigRef.current = initialConfig;
    setWorkflowConfig(initialConfig || {
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

    if (initialConfig && initialConfig.nodes && initialConfig.nodes.length > 0) {
      // Edit mode: Load existing nodes
      const reactFlowNodes: Node[] = initialConfig.nodes.map((node, index) => {
        const reactFlowNode: Node = {
          id: String(node.id),  // Convert backend integer ID to string for React Flow
          type: node.type,
          position: node.position || { x: 100 + index * 200, y: 100 },
          data: {
            id: String(node.id),  // React Flow ID (string)
            backendId: node.id,    // Keep original backend ID (integer) for API calls
            label: node.config?.name || `${node.type.charAt(0).toUpperCase()}${node.type.slice(1)} Node`,
            config: node.config,
            onConfig: handleNodeConfig,
            onDelete: handleNodeDelete,
            onExecute: onExecuteNode,
            workflowId: workflowId,
            onExecuteTrigger: handleExecuteTrigger,
            onOpenChat: handleOpenChat,
          }
        };

        return reactFlowNode;
      });

      const reactFlowEdges: Edge[] = initialConfig.edges.map(edge => {
        // Color-code edge based on target handle type
        const isContextInput = edge.targetHandle === 'context-input';
        const edgeColor = isContextInput ? '#f59e0b' : '#1173d4';  // Orange for context, blue for data

        return {
          id: `${edge.source}-${edge.target}`,
          source: String(edge.source),  // Convert to string for React Flow
          target: String(edge.target),  // Convert to string for React Flow
          targetHandle: edge.targetHandle,
          sourceHandle: edge.sourceHandle,
          type: 'smoothstep',
          animated: true,
          style: { stroke: edgeColor, strokeWidth: 2 }
        };
      });

      setNodes(reactFlowNodes);
      setEdges(reactFlowEdges);
    } else {
      // Create mode: Empty canvas
      setNodes([]);
      setEdges([]);
    }

    setInitialized(true);
  }, [initialConfig, hasInitialized, isLoading, handleNodeConfig, handleNodeDelete, onExecuteNode, workflowId, handleExecuteTrigger, handleOpenChat]);

  // Only notify parent when nodes/edges change directly - no state sync
  useEffect(() => {
    if (!initialized) return;

    // Create config directly from React Flow state without updating local state
    const currentConfig: WorkflowConfig = {
      nodes: nodes.map((node) => ({
        // Convert React Flow string ID back to integer for backend
        // Use backendId if available, otherwise parse the string ID
        id: node.data?.backendId || (isNaN(Number(node.id)) ? node.id : Number(node.id)),
        type: node.type || 'default',
        position: node.position,
        config: node.data?.config || {}
      })),
      edges: edges.map((edge) => ({
        id: edge.id,
        // Convert string IDs back to integers for backend
        source: isNaN(Number(edge.source)) ? edge.source : Number(edge.source),
        target: isNaN(Number(edge.target)) ? edge.target : Number(edge.target),
        targetHandle: edge.targetHandle,
        sourceHandle: edge.sourceHandle
      })),
      properties: workflowConfig.properties,
      metadata: {
        ...workflowConfig.metadata,
        updated: new Date().toISOString()
      }
    };

    // Notify parent directly without updating local state
    onConfigChange?.(currentConfig);

  }, [nodes, edges, initialized, workflowConfig]);

  // Set initial viewport to prevent zoom issues
  const defaultViewport = { x: 0, y: 0, zoom: 0.8 };

  const openNodeConfig = useCallback((nodeId: string, nodeType: string, nodeData: any) => {
    setConfigModal({
      isOpen: true,
      nodeId,
      nodeType,
      nodeData,
      edges: edges,
      nodes: nodes,
      executionCache: nodeExecutionCache || {},
    });
  }, [edges, nodes, nodeExecutionCache]);

  const closeNodeConfig = useCallback(() => {
    setConfigModal({
      isOpen: false,
      nodeId: null,
      nodeType: null,
      nodeData: null,
      edges: [],
      nodes: [],
      executionCache: {},
    });
  }, []);

  const saveNodeConfig = useCallback((newConfig: any) => {
    if (!configModal.nodeId) return;


    setNodes((nodes) =>
      nodes.map((node) =>
        node.id === configModal.nodeId
          ? { ...node, data: { ...node.data, config: newConfig } }
          : node
      )
    );


    closeNodeConfig();
  }, [configModal.nodeId, configModal.nodeType, setNodes, closeNodeConfig]);

  // Workflow properties modal handlers
  const openPropertiesModal = useCallback(() => {
    setPropertiesModal({ isOpen: true });
  }, []);

  const closePropertiesModal = useCallback(() => {
    setPropertiesModal({ isOpen: false });
  }, []);

  const saveWorkflowProperties = useCallback((newProperties: any) => {
    setWorkflowConfig(prev => {
      const updatedConfig = {
        ...prev,
        properties: { ...newProperties },
        metadata: {
          ...prev.metadata,
          updated: new Date().toISOString()
        }
      };


      return updatedConfig;
    });
  }, []);

  // Handle node double-click
  const onNodeDoubleClick = useCallback((event: any, node: any) => {
    event.stopPropagation();
    openNodeConfig(node.id, node.type, node.data);
  }, [openNodeConfig]);

  // Delete node function
  const deleteNode = useCallback((nodeId: string) => {
    setNodes((nodes) => nodes.filter((node) => node.id !== nodeId));
    setEdges((edges) => edges.filter((edge) =>
      edge.source !== nodeId && edge.target !== nodeId
    ));
  }, [setNodes, setEdges]);

  // Update node config
  const updateNodeConfig = useCallback((nodeId: string, config: Record<string, any>) => {
    setNodes((nodes) =>
      nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, config } }
          : node
      )
    );
  }, [setNodes]);

  // Connect nodes
  const onConnect = useCallback(
    (params: any) => {
      // Color-code edge based on target handle type
      const isContextInput = params.targetHandle === 'context-input';
      const edgeColor = isContextInput ? '#f59e0b' : '#1173d4';  // Orange for context, blue for data

      const newEdge = {
        ...params,
        id: `${params.source}-${params.target}-${Date.now()}`,
        type: 'smoothstep',
        animated: true,
        style: { stroke: edgeColor, strokeWidth: 2 },
      };
      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');

      if (typeof type === 'undefined' || !type) {
        return;
      }

      const reactFlowBounds = event.currentTarget.getBoundingClientRect();
      const position = {
        x: event.clientX - reactFlowBounds.left - 100,
        y: event.clientY - reactFlowBounds.top - 50,
      };

      const nodeId = `${type}-${Date.now()}`;
      const newNode = {
        id: nodeId,
        type,
        position,
        data: {
          label: `${type.charAt(0).toUpperCase() + type.slice(1)} Node`,
          onDelete: deleteNode,
          onConfig: openNodeConfig,
          onConfigChange: updateNodeConfig,
          onExecute: onExecuteNode,
          id: nodeId,
          config: getDefaultConfig(type),
          workflowId: workflowId,
          onExecuteTrigger: handleExecuteTrigger,
          onOpenChat: handleOpenChat,
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes, deleteNode, openNodeConfig, updateNodeConfig, onExecuteNode, workflowId, handleExecuteTrigger, handleOpenChat]
  );

  // Get default config for node type
  const getDefaultConfig = (nodeType: string) => {
    switch (nodeType) {
      case 'trigger_manual':
        return {
          description: '',
          initial_data: ''
        };
      case 'trigger_schedule':
        return {
          schedule: '0 9 * * *',
          timezone: 'UTC',
          enabled: true,
          description: ''
        };
      case 'trigger_chat':
        return {
          welcome_message: 'Hi! Send me a message to start the workflow.',
          context_instructions: '',
          description: ''
        };
      case 'database':
        return {
          connectionString: '',
          query: '',
          table: ''
        };
      case 'agent':
        return {
          agentId: null,
          llm_credential_id: null,
          prompts: [],
          tools: []
        };
      case 'output':
        return {
          output_type: '',
          credential_id: '',
          table_name: '',
          file_path: '',
          file_format: ''
        };
      case 'filter':
        return {
          conditions: [],
          operator: 'AND'
        };
      case 'script':
        return {
          script: '',
          language: 'python',
          timeout: 30
        };
      case 'conditional':
        return {
          condition: '',
          operator: '=='
        };
      default:
        return {};
    }
  };

  return (
    <div className="w-full h-full flex">
      {/* Canvas Container */}
      <div className={`relative transition-all ${chatOpen ? 'w-[65%]' : 'w-full'}`}>
        {/* Workflow Toolbar */}
        <div className="absolute top-4 left-4 z-50 flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={openPropertiesModal}
            leftIcon={<span className="material-symbols-outlined text-sm">settings</span>}
            className="bg-[#1a2633] border-[#374151] text-white hover:bg-[#233648]"
          >
            Properties
          </Button>
        </div>

        <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onNodeDoubleClick={onNodeDoubleClick}
        nodeTypes={nodeTypes}
        connectionMode="loose"
        className="bg-[#111a22]"
        connectionLineStyle={{ stroke: '#1173d4', strokeWidth: 2 }}
        defaultEdgeOptions={{
          style: { stroke: '#1173d4', strokeWidth: 2 },
          type: 'smoothstep',
          animated: true,
        }}
        nodesDraggable={true}
        nodesConnectable={true}
        elementsSelectable={true}
        selectNodesOnDrag={false}
        multiSelectionKeyCode="Shift"
        deleteKeyCode="Delete"
        snapToGrid={true}
        snapGrid={[15, 15]}
        fitView
        fitViewOptions={{
          padding: 0.2,
          minZoom: 0.1,
          maxZoom: 2
        }}
        minZoom={0.1}
        maxZoom={2}
        defaultViewport={defaultViewport}
        attributionPosition="bottom-left"
      >
        <Background
          color="#374151"
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
        />
        <Controls
          className="bg-[#1a2633] border border-[#374151] text-white"
          showZoom={true}
          showFitView={true}
          showInteractive={true}
          position="bottom-right"
        />
        <MiniMap
          className="bg-[#1a2633] border border-[#374151]"
          nodeColor="#1173d4"
          nodeStrokeColor="#374151"
          nodeStrokeWidth={1}
          maskColor="rgba(26, 38, 51, 0.8)"
        />

        {/* Enhanced empty state */}
        {nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center opacity-70 pointer-events-none z-10">
            <div className="text-center p-8 border-2 border-dashed border-[#374151] rounded-lg bg-[#111a22]/80 backdrop-blur-sm max-w-md">
              <span className="material-symbols-outlined text-6xl text-gray-400 mb-4 block">account_tree</span>
              <h3 className="text-white text-lg font-semibold mb-2">No Workflow Nodes</h3>
              <p className="text-gray-400 mb-4">
                This workflow doesn't have any nodes configured yet.
              </p>
              <div className="text-xs text-gray-500 space-y-1 text-left">
                <p>• Add nodes by editing this workflow</p>
                <p>• Drag from node palette to create workflow</p>
                <p>• Connect: data sources → agents → outputs</p>
              </div>
            </div>
          </div>
        )}
      </ReactFlow>

      {/* Node Configuration Modal */}
      <NodeConfigModal
        isOpen={configModal.isOpen}
        onClose={closeNodeConfig}
        nodeType={configModal.nodeType || ''}
        nodeData={configModal.nodeData}
        onSave={saveNodeConfig}
        edges={configModal.edges}
        nodes={configModal.nodes}
        nodeExecutionCache={configModal.executionCache}
        onExecuteNode={onExecuteNode}
      />

        {/* Workflow Properties Modal */}
        <WorkflowPropertiesModal
          isOpen={propertiesModal.isOpen}
          onClose={closePropertiesModal}
          onSave={saveWorkflowProperties}
          initialProperties={workflowConfig.properties}
        />
      </div>

      {/* Chat Panel */}
      {chatOpen && workflowId && (
        <div className="w-[35%] h-full">
          <WorkflowTriggerChat
            workflowId={workflowId}
            onClose={handleCloseChat}
            welcomeMessage={chatWelcomeMessage}
          />
        </div>
      )}

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}