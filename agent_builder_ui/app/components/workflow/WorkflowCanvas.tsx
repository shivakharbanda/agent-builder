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

interface WorkflowCanvasProps {
  onConfigChange?: (config: WorkflowConfig) => void;
  initialConfig?: WorkflowConfig;
  isLoading?: boolean;
  onExecuteNode?: (nodeId: string) => void;
  nodeExecutionCache?: Record<string, any>;
  workflowId?: number | null;
}

// Custom node components

// Trigger Nodes
function TriggerManualNode({ data, selected }: { data: any; selected: boolean }) {
  const [executing, setExecuting] = useState(false);

  const handleExecute = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!data.workflowId || executing) return;

    setExecuting(true);
    try {
      await data.onExecuteTrigger?.(data.workflowId);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className={`bg-[#1a3d2e] p-4 rounded-xl shadow-lg border-2 w-56 relative transition-all group ${
      selected ? 'border-green-500 shadow-xl shadow-green-500/30' : 'border-green-700/50'
    }`}>
      <div className="absolute -top-2 -right-2 bg-green-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
        START
      </div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-green-400 mr-2 text-2xl">play_circle</span>
          <h4 className="font-semibold text-white text-sm">{data.label || 'Manual Trigger'}</h4>
        </div>
        <div className="flex space-x-1">
          <button
            onClick={handleExecute}
            disabled={!data.workflowId || executing}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-400 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
            title={data.workflowId ? "Execute workflow" : "Save workflow first"}
          >
            <span className="material-symbols-outlined text-sm">{executing ? 'hourglass_empty' : 'play_arrow'}</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onConfig?.(data.id, 'trigger_manual', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-400 transition-opacity"
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
      <p className="text-xs text-gray-300">Run manually via button or API</p>
      {data.config?.description && (
        <div className="mt-2 text-xs text-green-300 truncate">{data.config.description}</div>
      )}
      {executing && (
        <div className="mt-2 text-xs text-green-400 animate-pulse">⚡ Executing...</div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-4 h-4 bg-green-500 border-2 border-white"
      />
    </div>
  );
}

function TriggerScheduleNode({ data, selected }: { data: any; selected: boolean }) {
  return (
    <div className={`bg-[#1a2e42] p-4 rounded-xl shadow-lg border-2 w-56 relative transition-all group ${
      selected ? 'border-blue-500 shadow-xl shadow-blue-500/30' : 'border-blue-700/50'
    }`}>
      <div className="absolute -top-2 -right-2 bg-blue-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
        START
      </div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-blue-400 mr-2 text-2xl">schedule</span>
          <h4 className="font-semibold text-white">{data.label || 'Schedule Trigger'}</h4>
        </div>
        <div className="flex space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onConfig?.(data.id, 'trigger_schedule', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-400 transition-opacity"
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
      <p className="text-xs text-gray-300">Run on recurring schedule</p>
      {data.config?.schedule && (
        <div className="mt-2 text-xs text-blue-300 font-mono bg-blue-950/50 px-2 py-1 rounded">
          {data.config.schedule}
        </div>
      )}
      {data.config?.enabled === false && (
        <div className="mt-1 text-xs text-yellow-400">⚠️ Schedule disabled</div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-4 h-4 bg-blue-500 border-2 border-white"
      />
    </div>
  );
}

function TriggerChatNode({ data, selected }: { data: any; selected: boolean }) {
  const handleOpenChat = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!data.workflowId) return;
    data.onOpenChat?.(data.config?.welcome_message);
  };

  return (
    <div className={`bg-[#2e1a42] p-4 rounded-xl shadow-lg border-2 w-56 relative transition-all group ${
      selected ? 'border-purple-500 shadow-xl shadow-purple-500/30' : 'border-purple-700/50'
    }`}>
      <div className="absolute -top-2 -right-2 bg-purple-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
        START
      </div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-purple-400 mr-2 text-2xl">chat</span>
          <h4 className="font-semibold text-white text-sm">{data.label || 'Chat Trigger'}</h4>
        </div>
        <div className="flex space-x-1">
          <button
            onClick={handleOpenChat}
            disabled={!data.workflowId}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-purple-400 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
            title={data.workflowId ? "Open chat" : "Save workflow first"}
          >
            <span className="material-symbols-outlined text-sm">forum</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onConfig?.(data.id, 'trigger_chat', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-purple-400 transition-opacity"
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
      <p className="text-xs text-gray-300">Start from user chat message</p>
      {data.config?.welcome_message && (
        <div className="mt-2 text-xs text-purple-300 italic truncate">
          "{data.config.welcome_message}"
        </div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-4 h-4 bg-purple-500 border-2 border-white"
      />
    </div>
  );
}

// Data Source Nodes
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
              console.log('Execute node:', { action: 'execute_node', nodeId: data.id, nodeType: 'database', config: data.config });
              data.onExecute?.(data.id, 'database', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-400 transition-opacity"
            title="Execute node"
          >
            <span className="material-symbols-outlined text-sm">play_arrow</span>
          </button>
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
              console.log('Execute node:', { action: 'execute_node', nodeId: data.id, nodeType: 'agent', config: data.config });
              data.onExecute?.(data.id, 'agent', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-400 transition-opacity"
            title="Execute node"
          >
            <span className="material-symbols-outlined text-sm">play_arrow</span>
          </button>
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

      {/* Data Input Handle - Top Left (Blue) */}
      <Handle
        type="target"
        position={Position.Left}
        id="data-input"
        className="w-4 h-4 bg-[#1173d4] border-2 border-white"
        style={{ top: '35%' }}
      />

      {/* Context Input Handle - Bottom Left (Orange) */}
      <Handle
        type="target"
        position={Position.Left}
        id="context-input"
        className="w-4 h-4 bg-[#f59e0b] border-2 border-white"
        style={{ top: '65%' }}
      />

      {/* Output Handle - Right */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
      />

      {/* Handle Labels */}
      <div className="absolute left-[-50px] top-[33%] text-[10px] text-gray-400">data</div>
      <div className="absolute left-[-60px] top-[63%] text-[10px] text-amber-400">context</div>
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
              console.log('Execute node:', { action: 'execute_node', nodeId: data.id, nodeType: 'output', config: data.config });
              data.onExecute?.(data.id, 'output', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-400 transition-opacity"
            title="Execute node"
          >
            <span className="material-symbols-outlined text-sm">play_arrow</span>
          </button>
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
              console.log('Execute node:', { action: 'execute_node', nodeId: data.id, nodeType: 'filter', config: data.config });
              data.onExecute?.(data.id, 'filter', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-400 transition-opacity"
            title="Execute node"
          >
            <span className="material-symbols-outlined text-sm">play_arrow</span>
          </button>
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
        <div className="flex space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              console.log('Execute node:', { action: 'execute_node', nodeId: data.id, nodeType: 'script', config: data.config });
              data.onExecute?.(data.id, 'script', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-400 transition-opacity"
            title="Execute node"
          >
            <span className="material-symbols-outlined text-sm">play_arrow</span>
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
        <div className="flex space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              console.log('Execute node:', { action: 'execute_node', nodeId: data.id, nodeType: 'conditional', config: data.config });
              data.onExecute?.(data.id, 'conditional', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-400 transition-opacity"
            title="Execute node"
          >
            <span className="material-symbols-outlined text-sm">play_arrow</span>
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