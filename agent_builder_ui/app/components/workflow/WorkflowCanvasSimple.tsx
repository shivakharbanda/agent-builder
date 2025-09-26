import { useCallback, useState, useEffect } from 'react';
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

interface WorkflowCanvasProps {
  onConfigChange?: (config: WorkflowConfig) => void;
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
      <p className="text-xs text-gray-400">Connects to your SQL database.</p>
      {data.config?.connectionString && (
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
      <p className="text-xs text-gray-400">Processes data with an AI agent.</p>
      {data.config?.agentId && (
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
          <span className="material-symbols-outlined text-[#1173d4] mr-2 text-xl">output</span>
          <h4 className="font-semibold text-white">{data.label || 'Output'}</h4>
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
      <p className="text-xs text-gray-400">Saves processed data to destination.</p>
      {data.config?.outputTable && (
        <div className="mt-2 text-xs text-green-400">✓ Output Configured</div>
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

const nodeTypes = {
  database: DatabaseNode,
  agent: AgentNode,
  output: OutputNode,
};

export function WorkflowCanvasSimple({ onConfigChange }: WorkflowCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node[]>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge[]>([]);

  const [workflowConfig, setWorkflowConfig] = useState<WorkflowConfig>({
    nodes: [],
    edges: [],
    metadata: {
      name: 'Untitled Workflow',
      description: '',
      version: '1.0.0',
      created: new Date().toISOString(),
      updated: new Date().toISOString(),
    }
  });

  // Update config whenever nodes or edges change
  useEffect(() => {
    setWorkflowConfig(prev => ({
      ...prev,
      nodes: nodes.map((node: any) => ({
        id: node.id,
        type: node.type,
        position: node.position,
        config: node.data?.config || {}
      })),
      edges: edges.map((edge: any) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target
      })),
      metadata: {
        ...prev.metadata,
        updated: new Date().toISOString()
      }
    }));
  }, [nodes, edges]);

  // Update parent component when config changes
  useEffect(() => {
    onConfigChange?.(workflowConfig);
  }, [workflowConfig, onConfigChange]);

  // Delete node function
  const deleteNode = useCallback((nodeId: string) => {
    setNodes((nodes: any) => nodes.filter((node: any) => node.id !== nodeId));
    setEdges((edges: any) => edges.filter((edge: any) =>
      edge.source !== nodeId && edge.target !== nodeId
    ));
  }, [setNodes, setEdges]);

  // Update node config
  const updateNodeConfig = useCallback((nodeId: string, config: Record<string, any>) => {
    setNodes((nodes: any) =>
      nodes.map((node: any) =>
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
      setEdges((eds: any) => addEdge(newEdge, eds));
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
          onConfigChange: updateNodeConfig,
          id: nodeId,
          config: getDefaultConfig(type)
        },
      };

      setNodes((nds: any) => nds.concat(newNode));
    },
    [setNodes, deleteNode, updateNodeConfig]
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
          outputTable: '',
          format: 'json'
        };
      default:
        return {};
    }
  };

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onDragOver={onDragOver}
      onDrop={onDrop}
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
        showInteractive={false}
      />
      <MiniMap
        className="bg-[#1a2633] border border-[#374151]"
        nodeColor="#1173d4"
        nodeStrokeColor="#374151"
        nodeStrokeWidth={1}
        maskColor="rgba(26, 38, 51, 0.8)"
      />

      {/* Empty state */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center opacity-50 pointer-events-none z-10">
          <div className="text-center p-8 border-2 border-dashed border-[#374151] rounded-lg bg-[#111a22]/80 backdrop-blur-sm">
            <span className="material-symbols-outlined text-6xl text-gray-400 mb-4 block">add</span>
            <p className="text-gray-400 mb-2">Drag a node here to start building</p>
            <div className="text-xs text-gray-500 space-y-1">
              <p>• Drag nodes from the sidebar</p>
              <p>• Connect nodes by dragging from handles</p>
              <p>• Delete with Del key or click X button</p>
              <p>• Multi-select with Shift + click</p>
            </div>
          </div>
        </div>
      )}
    </ReactFlow>
  );
}