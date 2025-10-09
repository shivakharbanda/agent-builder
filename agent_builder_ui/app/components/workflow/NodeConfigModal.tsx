import { useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { Input, Textarea, Select } from '../ui/Input';
import nodeConfigs from './config/nodeConfigs.json';
import { useCredentials, useAgents, useInternalTools } from '../../hooks/useAPI';
import { APP_CONFIG } from '../../lib/config';
import { api } from '../../lib/api';
import type { AgentCompleteCreate, Agent, InternalTool, Credential } from '../../lib/types';

interface NodeConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodeType: string;
  nodeData: any;
  onSave: (config: any) => void;
  edges?: any[];
  nodes?: any[];
  nodeExecutionCache?: Record<string, any>;
  onExecuteNode?: (nodeId: string) => void;
}

interface NodeConfig {
  name: string;
  description: string;
  icon: string;
  category: string;
  fields: any[];
  inputs?: any[];
  outputs?: any[];
}

// ============================================================================
// SUB-COMPONENTS - Defined outside to prevent re-mounting on state changes
// ============================================================================

// Tab Navigation Component
type AgentTab = 'config' | 'details';

function TabNavigation({
  activeTab,
  onTabChange
}: {
  activeTab: AgentTab;
  onTabChange: (tab: AgentTab) => void;
}) {
  return (
    <div className="flex border-b border-[#374151]">
      <button
        onClick={() => onTabChange('config')}
        className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 ${
          activeTab === 'config'
            ? 'border-[#1173d4] text-white'
            : 'border-transparent text-gray-400 hover:text-white'
        }`}
      >
        <span className="material-symbols-outlined text-sm mr-2 align-middle">settings</span>
        Configuration
      </button>

      <button
        onClick={() => onTabChange('details')}
        className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 ${
          activeTab === 'details'
            ? 'border-[#1173d4] text-white'
            : 'border-transparent text-gray-400 hover:text-white'
        }`}
      >
        <span className="material-symbols-outlined text-sm mr-2 align-middle">description</span>
        Agent Details
      </button>
    </div>
  );
}

// Agent Details Read-Only Component
function AgentDetailsReadOnly({ agent, onEdit }: { agent: Agent; onEdit?: () => void }) {
  const systemPrompt = agent.prompts?.find(p => p.prompt_type === 'system');
  const userPrompt = agent.prompts?.find(p => p.prompt_type === 'user');

  // Extract unique placeholders from both prompts
  const extractPlaceholders = () => {
    const placeholders = new Set<string>();

    if (systemPrompt?.placeholders) {
      Object.keys(systemPrompt.placeholders).forEach(key => placeholders.add(key));
    }
    if (userPrompt?.placeholders) {
      Object.keys(userPrompt.placeholders).forEach(key => placeholders.add(key));
    }

    return Array.from(placeholders);
  };

  const inputPlaceholders = extractPlaceholders();

  return (
    <div className="space-y-6">
      {/* Header with Edit Button */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 bg-gray-500/20 text-gray-400 text-xs rounded-full">
            READ-ONLY
          </span>
          {onEdit && (
            <Button onClick={onEdit} variant="outline" className="text-sm">
              <span className="material-symbols-outlined text-sm mr-1">edit</span>
              Edit Agent
            </Button>
          )}
        </div>
      </div>

      {/* Basic Info Card */}
      <div className="bg-[#0a1219] border border-[#374151] rounded-lg p-4 space-y-3">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
          <span className="material-symbols-outlined text-sm">info</span>
          <span>Basic Information</span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-gray-500">Name</div>
            <div className="text-sm text-white mt-1">{agent.name}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Return Type</div>
            <div className="mt-1">
              <span className={`text-xs px-2 py-1 rounded ${
                agent.return_type === 'structured'
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'bg-green-500/20 text-green-400'
              }`}>
                {agent.return_type}
              </span>
            </div>
          </div>
        </div>

        <div>
          <div className="text-xs text-gray-500">Description</div>
          <div className="text-sm text-white mt-1">{agent.description}</div>
        </div>
      </div>

      {/* System Prompt Card */}
      <div className="bg-[#0a1219] border border-[#374151] rounded-lg p-4">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
          <span className="material-symbols-outlined text-sm">chat</span>
          <span>System Prompt</span>
        </div>
        <pre className="text-xs text-gray-300 bg-[#111a22] p-3 rounded overflow-x-auto whitespace-pre-wrap">
          {systemPrompt?.content}
        </pre>
      </div>

      {/* User Prompt Card */}
      <div className="bg-[#0a1219] border border-[#374151] rounded-lg p-4">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
          <span className="material-symbols-outlined text-sm">person</span>
          <span>User Prompt Template</span>
        </div>
        <pre className="text-xs text-gray-300 bg-[#111a22] p-3 rounded overflow-x-auto whitespace-pre-wrap">
          {userPrompt?.content}
        </pre>
      </div>

      {/* Placeholders Card */}
      {inputPlaceholders.length > 0 && (
        <div className="bg-[#0a1219] border border-[#374151] rounded-lg p-4">
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
            <span className="material-symbols-outlined text-sm">label</span>
            <span>Input Placeholders</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {inputPlaceholders.map((ph: string) => (
              <span
                key={ph}
                className="px-3 py-1 bg-[#1173d4]/20 text-[#1173d4] text-sm rounded-full"
              >
                {ph}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Schema Card (if structured) */}
      {agent.return_type === 'structured' && agent.schema_definition && (
        <div className="bg-[#0a1219] border border-[#374151] rounded-lg p-4">
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
            <span className="material-symbols-outlined text-sm">code</span>
            <span>Output Schema</span>
          </div>
          <pre className="text-xs text-gray-300 bg-[#111a22] p-3 rounded overflow-x-auto">
            {JSON.stringify(agent.schema_definition, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// Agent Details Create Component
function AgentDetailsCreate({
  config,
  onChange,
  onCreateAgent,
  loading
}: {
  config: {
    name: string;
    description: string;
    return_type: 'structured' | 'unstructured';
    system_prompt: string;
    user_prompt: string;
    schema_definition: string;
  };
  onChange: (config: any) => void;
  onCreateAgent: () => void;
  loading: boolean;
}) {
  const [detectedPlaceholders, setDetectedPlaceholders] = useState<string[]>([]);

  // Auto-detect placeholders from prompts
  useEffect(() => {
    const placeholders = new Set<string>();
    const regex = /\{\{(\w+)\}\}/g;
    const combinedText = `${config.system_prompt} ${config.user_prompt}`;
    let match;

    while ((match = regex.exec(combinedText)) !== null) {
      placeholders.add(match[1]);
    }

    setDetectedPlaceholders(Array.from(placeholders));
  }, [config.system_prompt, config.user_prompt]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Create New Agent</h3>
      </div>

      {/* Agent Name */}
      <Input
        label="Agent Name"
        value={config.name}
        onChange={(e) => onChange({ ...config, name: e.target.value })}
        placeholder="e.g., Custom Sentiment Analyzer"
        required
      />

      {/* Description */}
      <Textarea
        label="Description"
        value={config.description}
        onChange={(e) => onChange({ ...config, description: e.target.value })}
        placeholder="What does this agent do?"
        className="min-h-[60px]"
      />

      {/* Return Type - Radio Buttons */}
      <div>
        <label className="block text-sm font-medium text-white mb-3">
          Return Type
          <span className="text-red-400 ml-1">*</span>
        </label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="structured"
              checked={config.return_type === 'structured'}
              onChange={(e) => onChange({ ...config, return_type: e.target.value as any })}
              className="w-4 h-4 text-[#1173d4]"
            />
            <span className="text-sm text-white">Structured (JSON)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="unstructured"
              checked={config.return_type === 'unstructured'}
              onChange={(e) => onChange({ ...config, return_type: e.target.value as any })}
              className="w-4 h-4 text-[#1173d4]"
            />
            <span className="text-sm text-white">Unstructured (Text)</span>
          </label>
        </div>
      </div>

      {/* System Prompt */}
      <Textarea
        label="System Prompt"
        value={config.system_prompt}
        onChange={(e) => onChange({ ...config, system_prompt: e.target.value })}
        placeholder="You are an expert at analyzing sentiment..."
        className="min-h-[120px]"
        required
        helperText="💡 Use {{placeholder}} for dynamic inputs"
      />

      {/* User Prompt */}
      <Textarea
        label="User Prompt Template"
        value={config.user_prompt}
        onChange={(e) => onChange({ ...config, user_prompt: e.target.value })}
        placeholder="Analyze this text: {{text}}"
        className="min-h-[80px]"
        required
        helperText="💡 Use {{placeholder}} for dynamic inputs"
      />

      {/* Auto-detected Placeholders */}
      {detectedPlaceholders.length > 0 && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-blue-400 text-sm mb-2">
            <span className="material-symbols-outlined text-sm">auto_awesome</span>
            <span>Auto-detected placeholders:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {detectedPlaceholders.map(ph => (
              <span key={ph} className="px-3 py-1 bg-blue-500/20 text-blue-400 text-sm rounded-full">
                {ph}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Schema (if structured) */}
      {config.return_type === 'structured' && (
        <Textarea
          label="Output Schema (JSON)"
          value={config.schema_definition}
          onChange={(e) => onChange({ ...config, schema_definition: e.target.value })}
          placeholder={`{
  "type": "object",
  "properties": {
    "sentiment": {"type": "string"},
    "confidence": {"type": "number"}
  }
}`}
          className="min-h-[200px] font-mono text-xs"
          required
        />
      )}

      {/* Create Button */}
      <Button
        onClick={onCreateAgent}
        disabled={!config.name || !config.system_prompt || !config.user_prompt || loading}
        className="w-full"
        loading={loading}
      >
        <span className="material-symbols-outlined text-sm mr-2">add</span>
        Create & Use Agent
      </Button>
    </div>
  );
}

// Agent Details Edit Component (for updating existing agents)
function AgentDetailsEdit({
  agent,
  config,
  onChange,
  onSave,
  onCancel,
  loading
}: {
  agent: Agent;
  config: {
    name: string;
    description: string;
    return_type: 'structured' | 'unstructured';
    system_prompt: string;
    user_prompt: string;
    schema_definition: string;
  };
  onChange: (config: any) => void;
  onSave: () => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [detectedPlaceholders, setDetectedPlaceholders] = useState<string[]>([]);

  // Auto-detect placeholders from prompts
  useEffect(() => {
    const placeholders = new Set<string>();
    const regex = /\{\{(\w+)\}\}/g;
    const combinedText = `${config.system_prompt} ${config.user_prompt}`;
    let match;

    while ((match = regex.exec(combinedText)) !== null) {
      placeholders.add(match[1]);
    }

    setDetectedPlaceholders(Array.from(placeholders));
  }, [config.system_prompt, config.user_prompt]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Edit Agent</h3>
        <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
          EDITING
        </span>
      </div>

      {/* Agent Name */}
      <Input
        label="Agent Name"
        value={config.name}
        onChange={(e) => onChange({ ...config, name: e.target.value })}
        placeholder="e.g., Custom Sentiment Analyzer"
        required
      />

      {/* Description */}
      <Textarea
        label="Description"
        value={config.description}
        onChange={(e) => onChange({ ...config, description: e.target.value })}
        placeholder="What does this agent do?"
        className="min-h-[60px]"
      />

      {/* Return Type - Radio Buttons */}
      <div>
        <label className="block text-sm font-medium text-white mb-3">
          Return Type
          <span className="text-red-400 ml-1">*</span>
        </label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="structured"
              checked={config.return_type === 'structured'}
              onChange={(e) => onChange({ ...config, return_type: e.target.value as any })}
              className="w-4 h-4 text-[#1173d4]"
            />
            <span className="text-sm text-white">Structured (JSON)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="unstructured"
              checked={config.return_type === 'unstructured'}
              onChange={(e) => onChange({ ...config, return_type: e.target.value as any })}
              className="w-4 h-4 text-[#1173d4]"
            />
            <span className="text-sm text-white">Unstructured (Text)</span>
          </label>
        </div>
      </div>

      {/* System Prompt */}
      <Textarea
        label="System Prompt"
        value={config.system_prompt}
        onChange={(e) => onChange({ ...config, system_prompt: e.target.value })}
        placeholder="You are an expert at analyzing sentiment..."
        className="min-h-[120px]"
        required
        helperText="💡 Use {{placeholder}} for dynamic inputs"
      />

      {/* User Prompt */}
      <Textarea
        label="User Prompt Template"
        value={config.user_prompt}
        onChange={(e) => onChange({ ...config, user_prompt: e.target.value })}
        placeholder="Analyze this text: {{text}}"
        className="min-h-[80px]"
        required
        helperText="💡 Use {{placeholder}} for dynamic inputs"
      />

      {/* Auto-detected Placeholders */}
      {detectedPlaceholders.length > 0 && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-blue-400 text-sm mb-2">
            <span className="material-symbols-outlined text-sm">auto_awesome</span>
            <span>Auto-detected placeholders:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {detectedPlaceholders.map(ph => (
              <span key={ph} className="px-3 py-1 bg-blue-500/20 text-blue-400 text-sm rounded-full">
                {ph}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Schema (if structured) */}
      {config.return_type === 'structured' && (
        <Textarea
          label="Output Schema (JSON)"
          value={config.schema_definition}
          onChange={(e) => onChange({ ...config, schema_definition: e.target.value })}
          placeholder={`{
  "type": "object",
  "properties": {
    "sentiment": {"type": "string"},
    "confidence": {"type": "number"}
  }
}`}
          className="min-h-[200px] font-mono text-xs"
          required
        />
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button
          onClick={onCancel}
          variant="outline"
          className="flex-1"
          disabled={loading}
        >
          Cancel
        </Button>
        <Button
          onClick={onSave}
          disabled={!config.name || !config.system_prompt || !config.user_prompt || loading}
          className="flex-1"
          loading={loading}
        >
          <span className="material-symbols-outlined text-sm mr-2">save</span>
          Save Changes
        </Button>
      </div>
    </div>
  );
}

export function NodeConfigModal({ isOpen, onClose, nodeType, nodeData, onSave, edges, nodes, nodeExecutionCache, onExecuteNode }: NodeConfigModalProps) {
  // Debug: Log props received
  console.log('[NodeConfigModal] Component props:', {
    isOpen,
    nodeType,
    nodeData,
    edgesCount: edges?.length,
    edges: edges,
    nodesCount: nodes?.length,
    nodes: nodes,
    hasCacheData: !!nodeExecutionCache,
    hasExecuteHandler: !!onExecuteNode
  });

  const [config, setConfig] = useState<any>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  // Tab system state
  const [activeTab, setActiveTab] = useState<AgentTab>('config');
  const [agentMode, setAgentMode] = useState<'select' | 'create'>('select');
  const [inlineAgentConfig, setInlineAgentConfig] = useState({
    name: '',
    description: '',
    return_type: 'structured' as 'structured' | 'unstructured',
    system_prompt: '',
    user_prompt: '',
    schema_definition: ''
  });

  // Full agent details state
  const [fullAgentDetails, setFullAgentDetails] = useState<Agent | null>(null);
  const [loadingAgentDetails, setLoadingAgentDetails] = useState(false);

  // Edit mode state for existing agents
  const [isEditingAgent, setIsEditingAgent] = useState(false);
  const [editAgentConfig, setEditAgentConfig] = useState({
    name: '',
    description: '',
    return_type: 'structured' as 'structured' | 'unstructured',
    system_prompt: '',
    user_prompt: '',
    schema_definition: ''
  });

  // Schema inspection state
  const [schemaData, setSchemaData] = useState<any>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  // Column loading state for input mapping
  const [columnLoadingState, setColumnLoadingState] = useState<{
    isLoading: boolean;
    executingNodes: Set<string>;
    errors: Record<string, string>;
  }>({
    isLoading: false,
    executingNodes: new Set(),
    errors: {}
  });

  // State for loaded columns from database nodes (via manual button click)
  const [loadedColumns, setLoadedColumns] = useState<Record<string, {
    columns: string[];
    data: Record<string, any>[];
    sourceLabel: string;
  }>>({});

  // Get node configuration from JSON
  const nodeConfig: NodeConfig = (nodeConfigs as any)[nodeType];

  // API hooks for fetching data
  const { data: credentials, loading: credentialsLoading, error: credentialsError } = useCredentials();
  const { data: agents, loading: agentsLoading, error: agentsError, refetch: refetchAgents } = useAgents();
  const { data: internalToolsData, loading: loadingInternalTools } = useInternalTools();

  // MCP Servers state
  const [mcpServers, setMcpServers] = useState<any[]>([]);

  useEffect(() => {
    // Debug logging
    if (isOpen) {
      console.log('[NodeConfigModal] Opening modal:', {
        nodeType,
        nodeData,
        hasConfig: !!nodeData?.config,
        configKeys: nodeData?.config ? Object.keys(nodeData.config) : [],
        config: nodeData?.config
      });
    }

    if (isOpen) {
      // Check if we have existing config with actual values (not just 'label')
      const hasExistingConfig = nodeData?.config &&
        Object.keys(nodeData.config).length > 0 &&
        Object.keys(nodeData.config).some(key => key !== 'label' && nodeData.config[key]);

      if (hasExistingConfig) {
        // Has existing config - use it
        console.log('[NodeConfigModal] Loading existing config:', nodeData.config);
        setConfig(nodeData.config);
      } else {
        // No config or only has label - initialize with defaults
        console.log('[NodeConfigModal] Initializing with defaults');
        const defaultConfig: any = {};
        nodeConfig?.fields?.forEach(field => {
          if (field.default !== undefined) {
            defaultConfig[field.name] = field.default;
          }
        });
        // If there's a label, preserve it
        if (nodeData?.config?.label) {
          defaultConfig.label = nodeData.config.label;
        }
        setConfig(defaultConfig);
      }
    }
  }, [isOpen, nodeData, nodeType, nodeConfig]);

  // Log connected database nodes when agent node config opens (auto-execute disabled to prevent infinite loops)
  useEffect(() => {
    if (!isOpen || nodeType !== 'agent') return;
    if (!edges || !nodes) return;

    const incomingEdges = edges.filter((edge: any) => edge.target === nodeData?.id);
    if (incomingEdges.length === 0) return;

    // Find source nodes that are database type
    const databaseNodes = incomingEdges
      .map((edge: any) => {
        const sourceNode = nodes?.find((n: any) => n.id === edge.source);
        return sourceNode;
      })
      .filter((node: any) => {
        if (!node) return false;
        return node.type === 'database';
      });

    if (databaseNodes.length > 0) {
      console.log('[NodeConfigModal] Connected database nodes detected:');
      databaseNodes.forEach(node => {
        const isExecuted = nodeExecutionCache?.[node.id];
        console.log(`  - ${node.data?.label || node.id} (${isExecuted ? 'executed' : 'not executed yet'})`);
        if (!isExecuted) {
          console.log(`    → User needs to execute this node manually to see columns in input mapping`);
        }
      });
    }
  }, [isOpen, nodeType, nodeData?.id, edges, nodes, nodeExecutionCache]);

  // Load MCP servers when modal opens
  useEffect(() => {
    const loadMcpServers = async () => {
      try {
        const response = await api.getMCPServers();
        setMcpServers(response.results || []);
      } catch (err) {
        console.error('Failed to load MCP servers:', err);
      }
    };

    if (isOpen) {
      loadMcpServers();
    }
  }, [isOpen]);

  // Handler to manually load columns from connected database nodes
  const handleLoadColumns = async () => {
    if (!edges || !nodes) return;

    const incomingEdges = edges.filter((edge: any) => edge.target === nodeData?.id);
    if (incomingEdges.length === 0) return;

    // Find database nodes
    const databaseNodes = incomingEdges
      .map((edge: any) => nodes?.find((n: any) => n.id === edge.source))
      .filter((node: any) => node?.type === 'database');

    if (databaseNodes.length === 0) return;

    setColumnLoadingState({
      isLoading: true,
      executingNodes: new Set(databaseNodes.map(n => n.id)),
      errors: {}
    });

    const newLoadedColumns: Record<string, any> = {};
    const errors: Record<string, string> = {};

    for (const node of databaseNodes) {
      const config = node.data?.config;

      if (!config?.credential_id || !config?.query) {
        console.log(`[NodeConfigModal] Skipping ${node.data?.label}: missing config`);
        errors[node.id] = 'Missing credential or query configuration';
        continue;
      }

      try {
        const result = await api.testDatabaseQuery(
          parseInt(config.credential_id),
          config.query
        );

        console.log(`[NodeConfigModal] Loaded columns from ${node.data?.label}:`, result.columns);

        newLoadedColumns[node.id] = {
          columns: result.columns,
          data: result.data,
          sourceLabel: node.data?.label || node.id
        };

      } catch (error: any) {
        const errorMsg = error.response?.data?.error || error.message || 'Failed to load columns';
        errors[node.id] = errorMsg;
        console.error(`[NodeConfigModal] Failed to load columns from ${node.data?.label}:`, error);
      }
    }

    setLoadedColumns(newLoadedColumns);
    setColumnLoadingState({
      isLoading: false,
      executingNodes: new Set(),
      errors
    });
  };

  const handleFieldChange = (fieldName: string, value: any) => {
    setConfig((prev: any) => ({
      ...prev,
      [fieldName]: value
    }));

    // Clear error when user starts typing
    if (errors[fieldName]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[fieldName];
        return newErrors;
      });
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};


    nodeConfig?.fields?.forEach(field => {
      // Check required fields (only for non-conditional fields)
      if (field.required && !field.conditional && (!config[field.name] || config[field.name] === '')) {
        newErrors[field.name] = `${field.label} is required`;
      }

      // Check conditional required fields
      if (field.conditional && shouldShowField(field)) {
        if (field.required && (!config[field.name] || config[field.name] === '')) {
          newErrors[field.name] = `${field.label} is required`;
        }
      }

      // Type-specific validation
      if (config[field.name]) {
        switch (field.type) {
          case 'number':
            const num = Number(config[field.name]);
            if (isNaN(num)) {
              newErrors[field.name] = `${field.label} must be a valid number`;
            } else {
              if (field.min !== undefined && num < field.min) {
                newErrors[field.name] = `${field.label} must be at least ${field.min}`;
              }
              if (field.max !== undefined && num > field.max) {
                newErrors[field.name] = `${field.label} must be at most ${field.max}`;
              }
            }
            break;
        }
      }
    });


    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      await onSave(config);
      onClose();
    } catch (error) {
    } finally {
      setLoading(false);
    }
  };

  const handleInspectSchema = async () => {
    const credentialId = config.credential_id;
    if (!credentialId) {
      setSchemaError('Please select a database credential first');
      return;
    }

    setSchemaLoading(true);
    setSchemaError(null);

    try {
      const schema = await api.inspectDatabaseSchema(Number(credentialId));
      setSchemaData(schema);
    } catch (error: any) {
      setSchemaError(error.response?.data?.error || error.message || 'Failed to inspect schema');
    } finally {
      setSchemaLoading(false);
    }
  };

  const toggleTableExpansion = (tableName: string) => {
    setExpandedTables(prev => {
      const newSet = new Set(prev);
      if (newSet.has(tableName)) {
        newSet.delete(tableName);
      } else {
        newSet.add(tableName);
      }
      return newSet;
    });
  };

  // Helper: Get available fields from trigger nodes based on their type
  const getTriggerFields = (triggerNode: any): string[] => {
    const triggerType = triggerNode.type;

    switch (triggerType) {
      case 'trigger_chat':
        return ['user_input', 'session_id', 'timestamp', '_trigger.type', '_trigger.session_id', '_trigger.description'];

      case 'trigger_manual':
        // Try to parse initial_data from config to get dynamic fields
        const initialData = triggerNode.data?.config?.initial_data;
        const baseFields = ['_trigger.type', '_trigger.description'];

        if (initialData) {
          try {
            const parsed = typeof initialData === 'string' ? JSON.parse(initialData) : initialData;
            if (typeof parsed === 'object' && !Array.isArray(parsed)) {
              // Extract top-level keys from initial_data object
              return [...Object.keys(parsed), ...baseFields];
            }
          } catch (e) {
            console.log('[getTriggerFields] Failed to parse initial_data:', e);
          }
        }
        return baseFields;

      case 'trigger_schedule':
        return ['_trigger.executed_at', '_trigger.schedule', '_trigger.timezone', '_trigger.type', '_trigger.description'];

      default:
        return [];
    }
  };

  // Get grouped column options from all incoming data source nodes (database + triggers)
  const getGroupedColumnOptions = () => {
    if (!edges || !nodeData?.id) {
      console.log('[getGroupedColumnOptions] Missing edges or nodeData.id:', { edges, nodeDataId: nodeData?.id });
      return { hasConnections: false, groups: [] };
    }

    console.log('[getGroupedColumnOptions] Debug info:', {
      nodeDataId: nodeData.id,
      totalEdges: edges.length,
      edges: edges,
      nodeData: nodeData
    });

    const incomingEdges = edges.filter((edge: any) => edge.target === nodeData.id);

    console.log('[getGroupedColumnOptions] Found incoming edges:', {
      count: incomingEdges.length,
      incomingEdges
    });

    if (incomingEdges.length === 0) {
      return { hasConnections: false, groups: [] };
    }

    const groups: Array<{
      sourceId: string;
      sourceLabel: string;
      columns: Array<{ value: string; label: string }>;
      hasResults: boolean;
      error?: string;
    }> = [];

    incomingEdges.forEach((edge: any) => {
      const sourceNodeId = edge.source;
      const sourceNode = nodes?.find((n: any) => n.id === sourceNodeId);
      const sourceLabel = sourceNode?.data?.label || sourceNode?.data?.config?.label || 'Unknown Source';
      const sourceType = sourceNode?.type;

      // Check if this is a trigger node
      if (sourceType?.startsWith('trigger_')) {
        // Handle trigger nodes - they provide predefined fields
        const triggerFields = getTriggerFields(sourceNode);

        groups.push({
          sourceId: sourceNodeId,
          sourceLabel: `${sourceLabel} (Trigger)`,
          columns: triggerFields.map(field => ({
            value: `${sourceNodeId}.${field}`,
            label: field
          })),
          hasResults: true,
          nodeType: 'trigger'
        });
      } else if (sourceType === 'database') {
        // Handle database nodes - check manually loaded columns first, then execution cache
        const loadedData = loadedColumns[sourceNodeId];
        const executionResults = nodeExecutionCache?.[sourceNodeId];
        const executionError = columnLoadingState.errors[sourceNodeId];

        if (executionError) {
          groups.push({
            sourceId: sourceNodeId,
            sourceLabel,
            columns: [],
            hasResults: false,
            error: executionError
          });
        } else if (loadedData && loadedData.columns.length > 0) {
          // Use manually loaded columns
          groups.push({
            sourceId: sourceNodeId,
            sourceLabel: loadedData.sourceLabel,
            columns: loadedData.columns.map(col => ({
              value: `${sourceNodeId}.${col}`,
              label: col
            })),
            hasResults: true,
            nodeType: 'database'
          });
        } else if (executionResults && executionResults.length > 0) {
          // Use execution cache columns
          const columnNames = Object.keys(executionResults[0]);
          groups.push({
            sourceId: sourceNodeId,
            sourceLabel,
            columns: columnNames.map(col => ({
              value: `${sourceNodeId}.${col}`,
              label: col
            })),
            hasResults: true,
            nodeType: 'database'
          });
        } else if (columnLoadingState.executingNodes.has(sourceNodeId)) {
          groups.push({
            sourceId: sourceNodeId,
            sourceLabel,
            columns: [],
            hasResults: false
          });
        } else {
          groups.push({
            sourceId: sourceNodeId,
            sourceLabel,
            columns: [],
            hasResults: false
          });
        }
      }
    });

    return { hasConnections: true, groups };
  };

  const shouldShowField = (field: any) => {
    if (!field.conditional) return true;

    const conditionValue = config[field.conditional.field];
    return conditionValue === field.conditional.value;
  };

  const renderField = (field: any) => {
    const fieldError = errors[field.name];
    const fieldValue = config[field.name] || '';

    // Don't render if conditional field is hidden
    if (!shouldShowField(field)) {
      return null;
    }

    switch (field.type) {
      case 'text':
      case 'textarea':
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            {field.type === 'textarea' ? (
              <textarea
                value={fieldValue}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
                placeholder={field.placeholder}
                rows={field.rows || 3}
                className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm resize-none ${
                  fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
                }`}
              />
            ) : (
              <Input
                type="text"
                value={fieldValue}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
                placeholder={field.placeholder}
                className={fieldError ? 'border-red-500' : ''}
              />
            )}
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      case 'number':
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <Input
              type="number"
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              placeholder={field.placeholder}
              min={field.min}
              max={field.max}
              className={fieldError ? 'border-red-500' : ''}
            />
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <select
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm ${
                fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
              }`}
            >
              <option value="">{field.placeholder || 'Select an option'}</option>
              {field.options?.map((option: any) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      case 'credential_select':
        // Filter credentials by category if specified
        const filteredCredentials = credentials?.results?.filter((cred: any) => {
          if (!field.category_filter) return true;
          // Check both possible field names for category
          return cred.credential_type?.category?.name === field.category_filter ||
                 cred.credential_type_category === field.category_filter ||
                 (cred.credential_type && cred.credential_type.includes(field.category_filter));
        }) || [];

        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <select
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              disabled={credentialsLoading}
              className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm ${
                fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
              } ${credentialsLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <option value="">
                {credentialsLoading ? 'Loading credentials...' : (field.placeholder || 'Select a credential')}
              </option>
              {credentialsError ? (
                <option disabled>Error loading credentials</option>
              ) : credentials?.results?.length === 0 ? (
                <option disabled>No credentials found</option>
              ) : filteredCredentials.length === 0 && field.category_filter ? (
                <option disabled>No {field.category_filter} credentials found</option>
              ) : (
                filteredCredentials.map((credential: any) => (
                  <option key={credential.id} value={credential.id}>
                    {credential.name} ({credential.credential_type?.type_name || credential.credential_type_name || 'Unknown Type'})
                  </option>
                ))
              )}
            </select>
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {/* Debug info */}
            {APP_CONFIG.ENABLE_DEBUG && (
              <div className="text-xs text-gray-500 mt-1">
                Total credentials: {credentials?.results?.length || 0},
                Filtered: {filteredCredentials.length}
                {field.category_filter && ` (filter: ${field.category_filter})`}
              </div>
            )}

            {/* Schema Inspector for Database Nodes */}
            {nodeType === 'database' && field.name === 'credential_id' && (
              <div className="mt-2">
                <button
                  type="button"
                  onClick={handleInspectSchema}
                  disabled={!fieldValue || schemaLoading}
                  className="text-sm px-3 py-1.5 bg-[#1173d4] hover:bg-[#0d5aa7] disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded flex items-center gap-1 transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">
                    {schemaLoading ? 'progress_activity' : 'schema'}
                  </span>
                  {schemaLoading ? 'Loading Schema...' : 'View Schema'}
                </button>

                {schemaError && (
                  <div className="mt-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded p-2">
                    {schemaError}
                  </div>
                )}

                {schemaData && (
                  <div className="mt-3 bg-[#0a1219] border border-[#374151] rounded-lg p-3 max-h-96 overflow-y-auto">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-white flex items-center gap-2">
                        <span className="material-symbols-outlined text-base">database</span>
                        {schemaData.metadata?.data_source_id || 'Unknown'} ({schemaData.database_type})
                      </h4>
                      <span className="text-xs text-gray-400">{schemaData.metadata?.tables?.length || 0} tables</span>
                    </div>

                    <div className="space-y-2">
                      {schemaData.metadata?.tables?.map((table: any) => {
                        const tableName = table.table_name;
                        const isExpanded = expandedTables.has(tableName);

                        return (
                          <div key={tableName} className="border border-[#374151] rounded">
                            <button
                              type="button"
                              onClick={() => toggleTableExpansion(tableName)}
                              className="w-full px-3 py-2 flex items-center justify-between hover:bg-[#111a22] transition-colors"
                            >
                              <span className="flex items-center gap-2 text-sm text-white">
                                <span className="material-symbols-outlined text-sm">
                                  {isExpanded ? 'expand_more' : 'chevron_right'}
                                </span>
                                <span className="material-symbols-outlined text-sm">table</span>
                                {tableName}
                              </span>
                              <span className="text-xs text-gray-400">
                                {table.columns?.length || 0} columns
                              </span>
                            </button>

                            {isExpanded && (
                              <div className="px-3 pb-3 pt-1 space-y-2">
                                <div>
                                  <p className="text-xs text-gray-400 mb-1">Columns:</p>
                                  <div className="space-y-1">
                                    {table.columns?.map((col: any, idx: number) => (
                                      <div
                                        key={idx}
                                        className="flex items-center gap-2 text-xs bg-[#111a22] rounded px-2 py-1"
                                      >
                                        <span className="material-symbols-outlined text-xs text-gray-400">
                                          {col.is_nullable === 'YES' ? 'toggle_off' : 'toggle_on'}
                                        </span>
                                        <span className="text-white font-mono">{col.column_name}</span>
                                        <span className="text-gray-400">({col.data_type})</span>
                                        {col.is_nullable === 'NO' && (
                                          <span className="text-red-400 text-[10px]">NOT NULL</span>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>

                                {table.sample_data && table.sample_data.length > 0 && (
                                  <div>
                                    <p className="text-xs text-gray-400 mb-1">Sample Data:</p>
                                    <div className="text-xs bg-[#111a22] rounded p-2 overflow-x-auto">
                                      <pre className="text-gray-300 font-mono">
                                        {JSON.stringify(table.sample_data, null, 2)}
                                      </pre>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );

      case 'agent_select':
        return (
          <div key={field.name} className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-white">
                {field.label}
                {field.required && <span className="text-red-400 ml-1">*</span>}
              </label>
              {fieldValue && (
                <button
                  type="button"
                  onClick={() => setActiveTab('details')}
                  className="text-xs text-[#1173d4] hover:text-[#0d5aa7] flex items-center gap-1"
                >
                  View Details
                  <span className="material-symbols-outlined text-xs">arrow_forward</span>
                </button>
              )}
            </div>
            <select
              value={fieldValue || ''}
              onChange={(e) => {
                if (e.target.value === '_create_new_') {
                  setAgentMode('create');
                  handleFieldChange(field.name, '');
                  setActiveTab('details'); // Auto-switch to details tab
                } else if (e.target.value === '') {
                  setAgentMode('select');
                  handleFieldChange(field.name, '');
                } else {
                  setAgentMode('select');
                  handleFieldChange(field.name, e.target.value);
                }
              }}
              disabled={agentsLoading}
              className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm ${
                fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
              } ${agentsLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <option value="">
                {agentsLoading ? 'Loading agents...' : (field.placeholder || 'Select an agent')}
              </option>
              {agentsError ? (
                <option disabled>Error loading agents</option>
              ) : agents?.results?.length === 0 ? (
                <option disabled>No agents found</option>
              ) : (
                <>
                  {agents?.results?.map((agent: any) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name} ({agent.return_type})
                    </option>
                  ))}
                  <option value="_create_new_">✨ Create New Agent</option>
                </>
              )}
            </select>
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {/* Debug info */}
            {APP_CONFIG.ENABLE_DEBUG && (
              <div className="text-xs text-gray-500 mt-1">
                Total agents: {agents?.results?.length || 0}
              </div>
            )}
          </div>
        );

      case 'code_editor':
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            <textarea
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              placeholder={field.placeholder}
              rows={field.rows || 8}
              className={`w-full bg-[#111a22] border rounded-md px-3 py-2 text-white text-sm font-mono resize-none ${
                fieldError ? 'border-red-500' : 'border-[#374151] focus:border-[#1173d4]'
              }`}
              style={{ fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace' }}
            />
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      case 'input_mapping':
        const selectedAgentId = config.agent_id;
        const selectedAgent = agents?.results?.find((a: any) => a.id === Number(selectedAgentId));
        const inputPlaceholders = selectedAgent?.input_placeholders || [];

        // Get grouped columns from execution results
        const { hasConnections, groups } = getGroupedColumnOptions();
        const isLoadingColumns = columnLoadingState.isLoading;

        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>

            {!selectedAgentId ? (
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 text-yellow-400 text-sm flex items-start gap-2">
                <span className="material-symbols-outlined text-sm mt-0.5">info</span>
                <span>Please select an agent first to configure input mapping</span>
              </div>
            ) : inputPlaceholders.length === 0 ? (
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-blue-400 text-sm flex items-start gap-2">
                <span className="material-symbols-outlined text-sm mt-0.5">info</span>
                <span>This agent doesn't have any input placeholders defined in its prompts</span>
              </div>
            ) : !hasConnections ? (
              <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-3 text-orange-400 text-sm flex items-start gap-2">
                <span className="material-symbols-outlined text-sm mt-0.5">warning</span>
                <span>No data sources connected. Connect a database or trigger node to this agent.</span>
              </div>
            ) : isLoadingColumns ? (
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                <div className="flex items-center gap-3 text-blue-400 text-sm mb-2">
                  <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                  <span>Executing connected database nodes to fetch columns...</span>
                </div>
                {Array.from(columnLoadingState.executingNodes).map(nodeId => {
                  const node = nodes?.find(n => n.id === nodeId);
                  return (
                    <div key={nodeId} className="ml-7 text-xs text-gray-400">
                      • {node?.data?.label || nodeId}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div>
                {/* Load Columns Button (only for database nodes) */}
                {groups.some(g => g.nodeType === 'database' && !g.hasResults) && (
                  <div className="mb-4 bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                    <p className="text-sm text-blue-400 mb-3 flex items-center gap-2">
                      <span className="material-symbols-outlined text-sm">info</span>
                      <span>Click below to load columns from connected database nodes (trigger fields are always available)</span>
                    </p>
                    <button
                      type="button"
                      onClick={handleLoadColumns}
                      className="w-full bg-[#1173d4] hover:bg-[#0d5aa7] text-white px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2"
                    >
                      <span className="material-symbols-outlined text-sm">cloud_download</span>
                      Load Columns from Database Nodes
                    </button>
                  </div>
                )}

                <p className="text-xs text-gray-400 mb-3">
                  Map input data fields to agent placeholders:
                </p>

                {/* Mapping Table */}
                <div className="border border-[#374151] rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-[#1a2633]">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                          Placeholder
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                          Map to Field
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-[#111a22] divide-y divide-[#374151]">
                      {inputPlaceholders.map((placeholder: string) => (
                        <tr key={placeholder} className="hover:bg-[#1a2633] transition-colors">
                          <td className="px-4 py-3">
                            <span className="text-sm text-white font-medium">
                              {placeholder}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <select
                              value={fieldValue?.[placeholder] || ''}
                              onChange={(e) => {
                                const newMapping = { ...(fieldValue || {}), [placeholder]: e.target.value };
                                handleFieldChange(field.name, newMapping);
                              }}
                              className="w-full bg-[#0a1219] border border-[#374151] rounded-md px-3 py-2 text-white text-sm focus:border-[#1173d4] focus:outline-none"
                            >
                              <option value="">-- Select field --</option>

                              {/* Grouped options by source node */}
                              {groups.map(group => {
                                if (group.error) {
                                  return (
                                    <optgroup key={group.sourceId} label={`${group.sourceLabel} (Error)`}>
                                      <option disabled value="">
                                        ⚠️ {group.error}
                                      </option>
                                    </optgroup>
                                  );
                                }

                                if (!group.hasResults) {
                                  return (
                                    <optgroup key={group.sourceId} label={`${group.sourceLabel} (No data)`}>
                                      <option disabled value="">
                                        Execute this node to see columns
                                      </option>
                                    </optgroup>
                                  );
                                }

                                return (
                                  <optgroup key={group.sourceId} label={group.sourceLabel}>
                                    {group.columns.map(col => (
                                      <option key={col.value} value={col.value}>
                                        {col.label}
                                      </option>
                                    ))}
                                  </optgroup>
                                );
                              })}
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Error Summary */}
                {Object.keys(columnLoadingState.errors).length > 0 && (
                  <div className="mt-3 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                    <p className="text-xs text-red-400 font-medium mb-2">
                      <span className="material-symbols-outlined text-xs mr-1">error</span>
                      Execution Errors:
                    </p>
                    <ul className="text-xs text-red-400 space-y-1 ml-5">
                      {Object.entries(columnLoadingState.errors).map(([nodeId, error]) => {
                        const node = nodes?.find(n => n.id === nodeId);
                        return (
                          <li key={nodeId}>
                            • {node?.data?.label || nodeId}: {error}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {/* Help text */}
                <div className="mt-3 bg-[#0a1219] border border-[#374151] rounded-lg p-3">
                  <p className="text-xs text-gray-400 flex items-center gap-1">
                    <span className="material-symbols-outlined text-xs">info</span>
                    Fields are automatically fetched from connected data sources (database columns, trigger fields)
                  </p>
                </div>
              </div>
            )}

            {field.help && (
              <p className="text-gray-400 text-xs mt-2">{field.help}</p>
            )}
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
          </div>
        );

      case 'internal_tool_multi_select':
        // Internal Tools multi-select (button + credential dropdown pairs)
        const internalTools = internalToolsData?.results || [];
        const allCredentials = credentials?.results || [];

        // Field value is stored as array of {tool_id, credential_id} objects
        const selectedToolAttachments = (fieldValue as Array<{tool_id: number, credential_id: number}>) || [];

        // Helper: Get credentials filtered by tool requirements
        const getCredentialsForTool = (tool: InternalTool): Credential[] => {
          if (!tool.requires_credential || !tool.required_credential_type) {
            return allCredentials;
          }
          return allCredentials.filter(
            cred => cred.credential_type === tool.required_credential_type
          );
        };

        // Helper: Check if tool is selected
        const isToolSelected = (toolId: number) => {
          return selectedToolAttachments.some(att => att.tool_id === toolId);
        };

        // Helper: Get selected credential ID for a tool
        const getSelectedCredentialId = (toolId: number): number => {
          const attachment = selectedToolAttachments.find(att => att.tool_id === toolId);
          return attachment?.credential_id || 0;
        };

        // Helper: Toggle tool selection
        const toggleInternalTool = (toolId: number, tool: InternalTool) => {
          if (isToolSelected(toolId)) {
            // Remove tool
            const newAttachments = selectedToolAttachments.filter(att => att.tool_id !== toolId);
            handleFieldChange(field.name, newAttachments);
          } else {
            // Add tool with auto-selected credential
            const matchingCreds = getCredentialsForTool(tool);
            const defaultCredId = matchingCreds.length > 0 ? matchingCreds[0].id : 0;
            const newAttachments = [...selectedToolAttachments, { tool_id: toolId, credential_id: defaultCredId }];
            handleFieldChange(field.name, newAttachments);
          }
        };

        // Helper: Update credential for a tool
        const updateInternalToolCredential = (toolId: number, credentialId: number) => {
          const newAttachments = selectedToolAttachments.map(att =>
            att.tool_id === toolId ? { ...att, credential_id: credentialId } : att
          );
          handleFieldChange(field.name, newAttachments);
        };

        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            {loadingInternalTools ? (
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-blue-400 text-sm">
                Loading internal tools...
              </div>
            ) : internalTools.length === 0 ? (
              <div className="bg-gray-500/10 border border-gray-500/20 rounded-lg p-3 text-gray-400 text-sm">
                No internal tools found. Please configure internal tools first.
              </div>
            ) : (
              <>
                <div className="space-y-3">
                  {internalTools.map(tool => {
                    const isSelected = isToolSelected(tool.id);
                    const selectedCredId = getSelectedCredentialId(tool.id);
                    const availableCreds = getCredentialsForTool(tool);

                    return (
                      <div key={tool.id} className="flex items-start gap-3">
                        <button
                          type="button"
                          onClick={() => toggleInternalTool(tool.id, tool)}
                          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex-shrink-0 ${
                            isSelected
                              ? 'bg-[#f59e0b] text-white'
                              : 'bg-[#233648] text-gray-300 hover:bg-[#2d4a5f]'
                          }`}
                        >
                          {tool.name}
                        </button>
                        {isSelected && (
                          <div className="flex-1">
                            <select
                              value={selectedCredId}
                              onChange={(e) => updateInternalToolCredential(tool.id, parseInt(e.target.value))}
                              className="w-full bg-[#111a22] border border-[#374151] rounded-md px-3 py-1.5 text-white text-sm focus:border-[#f59e0b] focus:outline-none"
                            >
                              <option value={0}>Select credential</option>
                              {availableCreds.map(cred => (
                                <option key={cred.id} value={cred.id}>
                                  {cred.name} ({cred.credential_type_name || 'Unknown Type'})
                                </option>
                              ))}
                            </select>
                            {availableCreds.length === 0 && (
                              <p className="text-yellow-400 text-xs mt-1">
                                ⚠️ No matching credentials found. Create a {tool.required_credential_type_name} credential.
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <p className="text-gray-500 text-xs mt-2">
                  Select internal tools and their credentials. {selectedToolAttachments.length} selected.
                </p>
              </>
            )}
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      case 'mcp_server_multi_select':
        // MCP Server multi-select (chip-based buttons)
        const selectedMcpServerIds = (fieldValue as number[]) || [];

        const toggleMcpServer = (serverId: number) => {
          const newSelection = selectedMcpServerIds.includes(serverId)
            ? selectedMcpServerIds.filter(id => id !== serverId)
            : [...selectedMcpServerIds, serverId];
          handleFieldChange(field.name, newSelection);
        };

        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </label>
            {mcpServers.length === 0 ? (
              <div className="bg-gray-500/10 border border-gray-500/20 rounded-lg p-3 text-gray-400 text-sm">
                No MCP servers found. Please register MCP servers in the Tools section.
              </div>
            ) : (
              <>
                <div className="flex flex-wrap gap-2">
                  {mcpServers.map(server => (
                    <button
                      key={server.id}
                      type="button"
                      onClick={() => toggleMcpServer(server.id)}
                      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                        selectedMcpServerIds.includes(server.id)
                          ? 'bg-[#f59e0b] text-white'
                          : 'bg-[#233648] text-gray-300 hover:bg-[#2d4a5f]'
                      }`}
                    >
                      {server.name}
                    </button>
                  ))}
                </div>
                <p className="text-gray-500 text-xs mt-2">
                  Select MCP servers to attach to this agent. {selectedMcpServerIds.length} selected.
                </p>
              </>
            )}
            {fieldError && (
              <p className="text-red-400 text-xs mt-1">{fieldError}</p>
            )}
            {field.help && (
              <p className="text-gray-400 text-xs mt-1">{field.help}</p>
            )}
          </div>
        );

      default:
        return (
          <div key={field.name} className="mb-4">
            <label className="block text-sm font-medium text-white mb-2">
              {field.label} (Unsupported field type: {field.type})
            </label>
            <Input
              type="text"
              value={fieldValue}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              placeholder={field.placeholder}
              disabled
            />
          </div>
        );
    }
  };

  // Get selected agent for details view
  const selectedAgent = agents?.results?.find((a: any) => a.id === Number(config.agent_id));

  // Fetch full agent details when switching to details tab
  useEffect(() => {
    const fetchAgentDetails = async () => {
      if (activeTab === 'details' && agentMode === 'select' && config.agent_id) {
        setLoadingAgentDetails(true);
        try {
          const agentDetails = await api.getAgent(Number(config.agent_id));
          setFullAgentDetails(agentDetails);
        } catch (error) {
          console.error('Failed to fetch agent details:', error);
          alert('Failed to load agent details. Please try again.');
        } finally {
          setLoadingAgentDetails(false);
        }
      } else {
        // Clear details when switching away from details tab
        setFullAgentDetails(null);
      }
    };

    fetchAgentDetails();
  }, [activeTab, agentMode, config.agent_id]);

  // Reset agent details when modal closes
  useEffect(() => {
    if (!isOpen) {
      setFullAgentDetails(null);
      setActiveTab('config');
      setAgentMode('select');
      setIsEditingAgent(false);
    }
  }, [isOpen]);

  // Exit edit mode when switching away from details tab
  useEffect(() => {
    if (activeTab !== 'details') {
      setIsEditingAgent(false);
    }
  }, [activeTab]);

  // Helper: Inline agent creation handler
  const handleCreateInlineAgent = async () => {
    try {
      setLoading(true);

      // Extract placeholders from prompts
      const placeholders: Record<string, string> = {};
      const regex = /\{\{(\w+)\}\}/g;
      const combinedText = `${inlineAgentConfig.system_prompt} ${inlineAgentConfig.user_prompt}`;
      let match;

      while ((match = regex.exec(combinedText)) !== null) {
        placeholders[match[1]] = `Input value for ${match[1]}`;
      }

      // Prepare agent data
      const agentData: AgentCompleteCreate = {
        name: inlineAgentConfig.name,
        description: inlineAgentConfig.description,
        return_type: inlineAgentConfig.return_type,
        project: 1, // TODO: Get from workflow/project context
        prompts: [
          {
            prompt_type: 'system',
            content: inlineAgentConfig.system_prompt,
            placeholders
          },
          {
            prompt_type: 'user',
            content: inlineAgentConfig.user_prompt,
            placeholders
          }
        ],
        schema_definition: inlineAgentConfig.return_type === 'structured'
          ? JSON.parse(inlineAgentConfig.schema_definition)
          : undefined
      };

      // Create agent via API
      const newAgent = await api.createAgentComplete(agentData);

      // Refetch agents list to include newly created agent
      await refetchAgents();

      // Set newly created agent as selected (now it will appear in dropdown)
      handleFieldChange('agent_id', newAgent.id.toString());

      // Switch back to select mode and config tab
      setAgentMode('select');
      setActiveTab('config');

      // Show success
      alert(`Agent "${newAgent.name}" created successfully!`);

    } catch (error: any) {
      console.error('Failed to create agent:', error);
      alert(error.message || 'Failed to create agent. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Helper: Enter edit mode for existing agent
  const enterEditMode = () => {
    if (!fullAgentDetails) return;

    const systemPrompt = fullAgentDetails.prompts?.find(p => p.prompt_type === 'system');
    const userPrompt = fullAgentDetails.prompts?.find(p => p.prompt_type === 'user');

    setEditAgentConfig({
      name: fullAgentDetails.name,
      description: fullAgentDetails.description,
      return_type: fullAgentDetails.return_type,
      system_prompt: systemPrompt?.content || '',
      user_prompt: userPrompt?.content || '',
      schema_definition: fullAgentDetails.schema_definition
        ? JSON.stringify(fullAgentDetails.schema_definition, null, 2)
        : ''
    });

    setIsEditingAgent(true);
  };

  // Helper: Update existing agent
  const handleUpdateAgent = async () => {
    if (!fullAgentDetails) return;

    try {
      setLoading(true);

      const systemPrompt = fullAgentDetails.prompts?.find(p => p.prompt_type === 'system');
      const userPrompt = fullAgentDetails.prompts?.find(p => p.prompt_type === 'user');

      // Extract placeholders from prompts
      const placeholders: Record<string, string> = {};
      const regex = /\{\{(\w+)\}\}/g;
      const combinedText = `${editAgentConfig.system_prompt} ${editAgentConfig.user_prompt}`;
      let match;

      while ((match = regex.exec(combinedText)) !== null) {
        placeholders[match[1]] = `Input value for ${match[1]}`;
      }

      // 1. Update agent basic info
      await api.updateAgent(fullAgentDetails.id, {
        name: editAgentConfig.name,
        description: editAgentConfig.description,
        return_type: editAgentConfig.return_type,
        schema_definition: editAgentConfig.return_type === 'structured'
          ? JSON.parse(editAgentConfig.schema_definition)
          : undefined,
        project: fullAgentDetails.project
      });

      // 2. Update system prompt
      if (systemPrompt) {
        await api.updatePrompt(systemPrompt.id, {
          agent: fullAgentDetails.id,
          prompt_type: 'system',
          content: editAgentConfig.system_prompt,
          placeholders
        });
      }

      // 3. Update user prompt
      if (userPrompt) {
        await api.updatePrompt(userPrompt.id, {
          agent: fullAgentDetails.id,
          prompt_type: 'user',
          content: editAgentConfig.user_prompt,
          placeholders
        });
      }

      // 4. Refetch full agent details
      const updatedAgent = await api.getAgent(fullAgentDetails.id);
      setFullAgentDetails(updatedAgent);

      // 5. Refetch agents list (to update dropdown)
      await refetchAgents();

      // 6. Exit edit mode
      setIsEditingAgent(false);

      // 7. Show success
      alert(`Agent "${editAgentConfig.name}" updated successfully!`);

    } catch (error: any) {
      console.error('Failed to update agent:', error);
      alert(error.message || 'Failed to update agent. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !nodeConfig) return null;

  // Check if this is an agent node to show tabs
  const showAgentTabs = nodeType === 'agent';

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className={`bg-[#1a2633] rounded-lg border border-[#374151] w-full ${showAgentTabs ? 'max-w-3xl' : 'max-w-2xl'} max-h-[90vh] overflow-hidden flex flex-col`}>
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-[#374151]">
            <div className="flex items-center space-x-3">
              <span className="material-symbols-outlined text-[#1173d4] text-2xl">
                {nodeConfig.icon}
              </span>
              <div>
                <h2 className="text-xl font-semibold text-white">
                  Configure {nodeConfig.name}
                </h2>
                <p className="text-gray-400 text-sm mt-1">
                  {nodeConfig.description}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          {/* Tab Navigation (only for agent nodes) */}
          {showAgentTabs && <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />}

          {/* API Errors */}
          {(credentialsError || agentsError) && (
            <div className="px-6 pt-4">
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                <div className="text-red-400 text-sm">
                  <span className="material-symbols-outlined text-sm mr-2">warning</span>
                  {credentialsError && `Credentials: ${credentialsError}`}
                  {credentialsError && agentsError && ' | '}
                  {agentsError && `Agents: ${agentsError}`}
                </div>
              </div>
            </div>
          )}

          {/* Content - Tab-based for agent nodes, normal for others */}
          <div className="flex-1 overflow-y-auto p-6">
            {showAgentTabs ? (
              activeTab === 'config' ? (
                // Configuration Tab
                <div className="space-y-6">
                  {nodeConfig.fields?.map(renderField)}
                </div>
              ) : (
                // Agent Details Tab
                <div>
                  {loadingAgentDetails ? (
                    <div className="flex flex-col items-center justify-center py-12">
                      <span className="material-symbols-outlined text-4xl text-[#1173d4] mb-4 animate-spin">
                        progress_activity
                      </span>
                      <p className="text-gray-400">Loading agent details...</p>
                    </div>
                  ) : agentMode === 'select' && fullAgentDetails ? (
                    isEditingAgent ? (
                      <AgentDetailsEdit
                        agent={fullAgentDetails}
                        config={editAgentConfig}
                        onChange={setEditAgentConfig}
                        onSave={handleUpdateAgent}
                        onCancel={() => setIsEditingAgent(false)}
                        loading={loading}
                      />
                    ) : (
                      <AgentDetailsReadOnly
                        agent={fullAgentDetails}
                        onEdit={enterEditMode}
                      />
                    )
                  ) : agentMode === 'create' ? (
                    <AgentDetailsCreate
                      config={inlineAgentConfig}
                      onChange={setInlineAgentConfig}
                      onCreateAgent={handleCreateInlineAgent}
                      loading={loading}
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <span className="material-symbols-outlined text-6xl text-gray-500 mb-4">
                        info
                      </span>
                      <p className="text-gray-400">
                        Select an agent from the Configuration tab to view details
                      </p>
                    </div>
                  )}
                </div>
              )
            ) : (
              // Non-agent nodes - render fields normally
              <div className="space-y-6">
                {nodeConfig.fields?.map(renderField)}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end space-x-3 p-6 border-t border-[#374151]">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined text-sm mr-1 animate-spin">
                    progress_activity
                  </span>
                  Saving...
                </>
              ) : (
                'Save Configuration'
              )}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}