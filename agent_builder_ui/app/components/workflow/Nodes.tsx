import {  useState } from 'react';
import {
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Trigger Nodes
export function TriggerManualNode({ data, selected }: { data: any; selected: boolean }) {
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



export function TriggerScheduleNode({ data, selected }: { data: any; selected: boolean }) {
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

export function TriggerChatNode({ data, selected }: { data: any; selected: boolean }) {
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
export function DatabaseNode({ data, selected }: { data: any; selected: boolean }) {
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

export function AgentNode({ data, selected }: { data: any; selected: boolean }) {
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

      {/* Tools Input Handle - Bottom (Amber) */}
      <Handle
        type="target"
        position={Position.Bottom}
        id="tools-input"
        className="w-4 h-4 bg-[#f59e0b] border-2 border-white"
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
      <div className="absolute bottom-[-18px] left-1/2 transform -translate-x-1/2 text-[10px] text-amber-400">tools</div>
    </div>
  );
}

// Toolbox Node
export function ToolboxNode({ data, selected }: { data: any; selected: boolean }) {
  // Count configured tools
  const mcpCount = data.config?.mcp_server_ids?.length || 0;
  const internalToolCount = data.config?.internal_tool_attachments?.length || 0;
  const totalTools = mcpCount + internalToolCount;

  return (
    <div className={`bg-[#2e1f0d] p-4 rounded-lg shadow-md border-2 w-48 relative transition-all group ${
      selected ? 'border-[#f59e0b] shadow-lg shadow-[#f59e0b]/20' : 'border-[#92400e]'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <span className="material-symbols-outlined text-[#f59e0b] mr-2 text-xl">construction</span>
          <h4 className="font-semibold text-white">{data.label || 'Toolbox'}</h4>
        </div>
        <div className="flex space-x-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onConfig?.(data.id, 'toolbox', data);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-[#f59e0b] transition-opacity"
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
      <p className="text-xs text-gray-400">Provides tools to AI agents</p>
      {totalTools > 0 ? (
        <div className="mt-2 text-xs text-[#f59e0b]">
          ✓ {totalTools} tool{totalTools !== 1 ? 's' : ''} configured
          {mcpCount > 0 && <div className="text-[10px] text-gray-500 mt-0.5">MCP: {mcpCount}</div>}
          {internalToolCount > 0 && <div className="text-[10px] text-gray-500">Internal: {internalToolCount}</div>}
        </div>
      ) : (
        <div className="mt-2 text-xs text-gray-500">No tools configured</div>
      )}

      {/* Output Handle - Top (connects to agent bottom) */}
      <Handle
        type="source"
        position={Position.Top}
        className="w-4 h-4 bg-[#f59e0b] border-2 border-white"
      />
    </div>
  );
}

export function OutputNode({ data, selected }: { data: any; selected: boolean }) {
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

export function FilterNode({ data, selected }: { data: any; selected: boolean }) {
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

export function ScriptNode({ data, selected }: { data: any; selected: boolean }) {
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

export function ConditionalNode({ data, selected }: { data: any; selected: boolean }) {
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