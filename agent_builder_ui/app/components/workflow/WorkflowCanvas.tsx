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
import { Button } from '../ui/Button';

interface WorkflowCanvasProps {
  onConfigChange?: (config: WorkflowConfig) => void;
  initialConfig?: WorkflowConfig;
  isLoading?: boolean;
}

// Custom node components
function DatabaseNode({ data, selected }: { data: any; selected: boolean }) {
  return (
    <div className={`bg-[#1a2633] p-4 rounded-lg shadow-md border-2 w-48 relative transition-all group ${
      selected ? 'border-[#1173d4] shadow-lg shadow-[#1173d4]/20' : 'border-[#374151]'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-[#1173d4] mr-2 text-xl">storage</span>
          <h4 className="font-semibold text-white">{data.label || 'Database'}</h4>
        </div>
        <div className="flex space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onConfig?.(data.id, 'database', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-[#1173d4] transition-opacity"
            title="Configure node"
          >
            <span className="material-symbols-outlined text-sm">settings</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onDelete?.(data.id);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition-opacity"
            title="Delete node"
          >
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </div>
      </div>
      <p className="text-xs text-gray-400">Connects to your SQL database.</p>
      {data.config?.credential_id && (
        <div className="mt-2 text-xs text-green-400">✓ Configured</div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />
    </div>
  );
}

function AgentNode({ data, selected }: { data: any; selected: boolean }) {
  return (
    <div className={`bg-[#1a2633] p-4 rounded-lg shadow-md border-2 w-48 relative transition-all group ${
      selected ? 'border-[#1173d4] shadow-lg shadow-[#1173d4]/20' : 'border-[#374151]'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-[#1173d4] mr-2 text-xl">smart_toy</span>
          <h4 className="font-semibold text-white">{data.label || 'Agent'}</h4>
        </div>
        <div className="flex space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onConfig?.(data.id, 'agent', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-[#1173d4] transition-opacity"
            title="Configure node"
          >
            <span className="material-symbols-outlined text-sm">settings</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onDelete?.(data.id);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition-opacity"
            title="Delete node"
          >
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </div>
      </div>
      <p className="text-xs text-gray-400">Processes data with an AI agent.</p>
      {data.config?.agent_id && (
        <div className="mt-2 text-xs text-green-400">✓ Agent Selected</div>
      )}

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />
    </div>
  );
}

function OutputNode({ data, selected }: { data: any; selected: boolean }) {
  return (
    <div className={`bg-[#1a2633] p-4 rounded-lg shadow-md border-2 w-48 relative transition-all group ${
      selected ? 'border-[#1173d4] shadow-lg shadow-[#1173d4]/20' : 'border-[#374151]'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-[#1173d4] mr-2 text-xl">save</span>
          <h4 className="font-semibold text-white">{data.label || 'Output'}</h4>
        </div>
        <div className="flex space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onConfig?.(data.id, 'output', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-[#1173d4] transition-opacity"
            title="Configure node"
          >
            <span className="material-symbols-outlined text-sm">settings</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onDelete?.(data.id);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition-opacity"
            title="Delete node"
          >
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </div>
      </div>
      <p className="text-xs text-gray-400">Saves processed data to destination.</p>
      {data.config?.output_type && (
        <div className="mt-2 text-xs text-green-400">
          ✓ {data.config.output_type === 'database' ? 'Database Output' :
             data.config.output_type === 'file' ? 'File Output' :
             data.config.output_type === 'api' ? 'API Output' : 'Output Configured'}
        </div>
      )}

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />
    </div>
  );
}

function FilterNode({ data, selected }: { data: any; selected: boolean }) {
  return (
    <div className={`bg-[#1a2633] p-4 rounded-lg shadow-md border-2 w-48 relative transition-all group ${
      selected ? 'border-[#1173d4] shadow-lg shadow-[#1173d4]/20' : 'border-[#374151]'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-[#1173d4] mr-2 text-xl">filter_alt</span>
          <h4 className="font-semibold text-white">{data.label || 'Filter'}</h4>
        </div>
        <div className="flex space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onConfig?.(data.id, 'filter', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-[#1173d4] transition-opacity"
            title="Configure node"
          >
            <span className="material-symbols-outlined text-sm">settings</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onDelete?.(data.id);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition-opacity"
            title="Delete node"
          >
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </div>
      </div>
      <p className="text-xs text-gray-400">Filters and selects data based on conditions.</p>
      {data.config?.conditions && (
        <div className="mt-2 text-xs text-green-400">✓ Filter Configured</div>
      )}

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />
    </div>
  );
}

function ScriptNode({ data, selected }: { data: any; selected: boolean }) {
  return (
    <div className={`bg-[#1a2633] p-4 rounded-lg shadow-md border-2 w-48 relative transition-all group ${
      selected ? 'border-[#1173d4] shadow-lg shadow-[#1173d4]/20' : 'border-[#374151]'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-[#1173d4] mr-2 text-xl">code</span>
          <h4 className="font-semibold text-white">{data.label || 'Script'}</h4>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            data.onDelete?.(data.id);
          }}
          className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition-opacity"
        >
          <span className="material-symbols-outlined text-sm">close</span>
        </button>
      </div>
      <p className="text-xs text-gray-400">Runs custom Python or JavaScript code.</p>
      {data.config?.script && (
        <div className="mt-2 text-xs text-green-400">✓ Script Configured</div>
      )}

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />
    </div>
  );
}

function ConditionalNode({ data, selected }: { data: any; selected: boolean }) {
  return (
    <div className={`bg-[#1a2633] p-4 rounded-lg shadow-md border-2 w-48 relative transition-all group ${
      selected ? 'border-[#1173d4] shadow-lg shadow-[#1173d4]/20' : 'border-[#374151]'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-[#1173d4] mr-2 text-xl">fork_right</span>
          <h4 className="font-semibold text-white">{data.label || 'Conditional'}</h4>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            data.onDelete?.(data.id);
          }}
          className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition-opacity"
        >
          <span className="material-symbols-outlined text-sm">close</span>
        </button>
      </div>
      <p className="text-xs text-gray-400">Branches workflow based on conditions.</p>
      {data.config?.condition && (
        <div className="mt-2 text-xs text-green-400">✓ Condition Configured</div>
      )}

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />
      {/* True Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="true"
        style={{ top: '30%' }}
        className="w-3 h-3 bg-green-500 border-2 border-[#1a2633]"
      />
      {/* False Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="false"
        style={{ top: '70%' }}
        className="w-3 h-3 bg-red-500 border-2 border-[#1a2633]"
      />
    </div>
  );
}

const nodeTypes = {
  database: DatabaseNode,
  agent: AgentNode,
  output: OutputNode,
  filter: FilterNode,
  script: ScriptNode,
  conditional: ConditionalNode,
};

export function WorkflowCanvas({ onConfigChange, initialConfig, isLoading }: WorkflowCanvasProps) {
  // React Flow manages node/edge arrays internally
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Node configuration modal state
  const [configModal, setConfigModal] = useState<{
    isOpen: boolean;
    nodeId: string | null;
    nodeType: string | null;
    nodeData: any | null;
  }>({
    isOpen: false,
    nodeId: null,
    nodeType: null,
    nodeData: null,
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
          id: node.id,
          type: node.type,
          position: node.position || { x: 100 + index * 200, y: 100 },
          data: {
            id: node.id,
            label: node.config?.name || `${node.type.charAt(0).toUpperCase()}${node.type.slice(1)} Node`,
            config: node.config,
            onConfig: handleNodeConfig,
            onDelete: handleNodeDelete,
          }
        };

        return reactFlowNode;
      });

      const reactFlowEdges: Edge[] = initialConfig.edges.map(edge => ({
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#1173d4', strokeWidth: 2 }
      }));

      setNodes(reactFlowNodes);
      setEdges(reactFlowEdges);
    } else {
      // Create mode: Empty canvas
      setNodes([]);
      setEdges([]);
    }

    setInitialized(true);
  }, [initialConfig, hasInitialized, isLoading]);

  // Only notify parent when nodes/edges change directly - no state sync
  useEffect(() => {
    if (!initialized) return;

    // Create config directly from React Flow state without updating local state
    const currentConfig: WorkflowConfig = {
      nodes: nodes.map((node) => ({
        id: node.id,
        type: node.type || 'default',
        position: node.position,
        config: node.data?.config || {}
      })),
      edges: edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target
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

  // Node configuration handlers
  const handleNodeConfig = useCallback((nodeId: string, nodeType: string, nodeData: any) => {
    setConfigModal({
      isOpen: true,
      nodeId,
      nodeType,
      nodeData,
    });
  }, []);

  const handleNodeDelete = useCallback((nodeId: string) => {
    setNodes((nodes) => nodes.filter((node) => node.id !== nodeId));
    setEdges((edges) => edges.filter((edge) =>
      edge.source !== nodeId && edge.target !== nodeId
    ));
  }, [setNodes, setEdges]);

  const openNodeConfig = useCallback((nodeId: string, nodeType: string, nodeData: any) => {
    setConfigModal({
      isOpen: true,
      nodeId,
      nodeType,
      nodeData,
    });
  }, []);

  const closeNodeConfig = useCallback(() => {
    setConfigModal({
      isOpen: false,
      nodeId: null,
      nodeType: null,
      nodeData: null,
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
      const newEdge = {
        ...params,
        id: `${params.source}-${params.target}-${Date.now()}`,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#1173d4', strokeWidth: 2 },
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
          id: nodeId,
          config: getDefaultConfig(type)
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes, deleteNode, openNodeConfig, updateNodeConfig]
  );

  // Get default config for node type
  const getDefaultConfig = (nodeType: string) => {
    switch (nodeType) {
      case 'database':
        return {
          connectionString: '',
          query: '',
          table: ''
        };
      case 'agent':
        return {
          agentId: null,
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
    <div className="w-full h-full relative">
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
      />

      {/* Workflow Properties Modal */}
      <WorkflowPropertiesModal
        isOpen={propertiesModal.isOpen}
        onClose={closePropertiesModal}
        onSave={saveWorkflowProperties}
        initialProperties={workflowConfig.properties}
      />
    </div>
  );
}