import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import type { Route } from './+types/create';
import { Layout } from '../../components/layout/Layout';
import { Input, Textarea, Select } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { LoadingState } from '../../components/ui/Loading';
import { useProjects, useTools, useFormSubmit } from '../../hooks/useAPI';
import { api } from '../../lib/api';
import type { AgentCompleteCreate, PromptCreateData, ReturnType, Tool } from '../../lib/types';
import { isValidJSON } from '../../lib/utils';
import { ChatInterface } from '../../components/agent-builder/ChatInterface';
import { validateAndTransformConfig } from '../../lib/agentConfigValidator';
import { ToastContainer } from '../../components/ui/Toast';
import { useToast } from '../../hooks/useToast';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Create Agent - Agent Builder" },
    { name: "description", content: "Define and configure a new agent to assist with your tasks" },
  ];
}

interface SelectedTool {
  id: number;
  name: string;
  tool_type: string;
  selected: boolean;
}

interface FormData {
  name: string;
  description: string;
  project: number;
  return_type: ReturnType;
  schema_definition: string;
  system_prompt: string;
  user_prompt: string;
  system_prompt_placeholders: Record<string, string>;
  user_prompt_placeholders: Record<string, string>;
}

type BuilderMode = 'manual' | 'ai';

export default function CreateAgent() {
  const navigate = useNavigate();
  const { data: projects, loading: projectsLoading } = useProjects();
  const { data: tools, loading: toolsLoading } = useTools();
  const { toasts, showToast, removeToast } = useToast();

  const [builderMode, setBuilderMode] = useState<BuilderMode>('ai');
  const [formHighlight, setFormHighlight] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    project: 0,
    return_type: 'unstructured',
    schema_definition: '',
    system_prompt: '',
    user_prompt: '',
    system_prompt_placeholders: {},
    user_prompt_placeholders: {},
  });

  const [selectedTools, setSelectedTools] = useState<SelectedTool[]>([]);
  const [schemaError, setSchemaError] = useState<string>('');

  const { loading: submitting, error, submit } = useFormSubmit(
    async (data: FormData) => {
      // Prepare prompts data
      const prompts: PromptCreateData[] = [];

      if (data.system_prompt) {
        prompts.push({
          prompt_type: 'system',
          content: data.system_prompt,
          placeholders: data.system_prompt_placeholders,
        });
      }

      if (data.user_prompt) {
        prompts.push({
          prompt_type: 'user',
          content: data.user_prompt,
          placeholders: data.user_prompt_placeholders,
        });
      }

      // Prepare tool IDs
      const tool_ids = selectedTools.filter(t => t.selected).map(t => t.id);

      // Create complete agent data
      const agentData: AgentCompleteCreate = {
        name: data.name,
        description: data.description,
        project: data.project,
        return_type: data.return_type,
        schema_definition: data.return_type === 'structured' && data.schema_definition
          ? JSON.parse(data.schema_definition)
          : undefined,
        prompts: prompts.length > 0 ? prompts : undefined,
        tool_ids: tool_ids.length > 0 ? tool_ids : undefined,
      };

      // Single atomic API call
      const agent = await api.createAgentComplete(agentData);
      return agent;
    }
  );

  // Initialize tools when they load
  useEffect(() => {
    if (tools?.results) {
      setSelectedTools(
        tools.results.map(tool => ({
          id: tool.id,
          name: tool.name,
          tool_type: tool.tool_type,
          selected: false,
        }))
      );
    }
  }, [tools]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required fields
    if (!formData.name.trim()) {
      return;
    }

    if (formData.project === 0) {
      return;
    }

    // Validate schema if structured
    if (formData.return_type === 'structured' && formData.schema_definition) {

      if (!isValidJSON(formData.schema_definition)) {
        setSchemaError('Invalid JSON schema');
        return;
      }
    }

    try {
      const agent = await submit(formData);
      navigate(`/agents/${agent.id}`);
    } catch (err) {
      // Error is handled by the hook
    }
  };

  const handleInputChange = (field: keyof FormData, value: string | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));

    if (field === 'schema_definition') {
      setSchemaError('');
    }
  };

  const toggleTool = (toolId: number) => {
    setSelectedTools(prev =>
      prev.map(tool =>
        tool.id === toolId ? { ...tool, selected: !tool.selected } : tool
      )
    );
  };

  const getToolIcon = (toolType: string) => {
    const iconMap: Record<string, string> = {
      search: 'search',
      code: 'code',
      database: 'storage',
      api: 'api',
      llm: 'auto_awesome',
      default: 'extension',
    };
    return iconMap[toolType] || iconMap.default;
  };

  // AI Chat handlers
  const handleAgentConfigComplete = (config: any) => {
    console.log('AI Agent Config:', config);

    // Get selected tools
    const selectedToolIds = selectedTools.filter(t => t.selected).map(t => t.id);

    // Validate and transform the configuration
    const validationResult = validateAndTransformConfig(
      config,
      formData.project,
      selectedToolIds
    );

    if (!validationResult.isValid) {
      console.error('Configuration validation failed:', validationResult.errors);
      showToast('Configuration validation failed. Please try again.', 'error');
      return;
    }

    const validatedConfig = validationResult.config!;

    // Populate form data from AI chat configuration
    setFormData(prev => ({
      ...prev,
      name: validatedConfig.name,
      description: validatedConfig.description,
      return_type: validatedConfig.return_type,
      schema_definition: validatedConfig.schema_definition ? JSON.stringify(validatedConfig.schema_definition, null, 2) : '',
      system_prompt: validatedConfig.prompts?.find((p: any) => p.prompt_type === 'system')?.content || '',
      user_prompt: validatedConfig.prompts?.find((p: any) => p.prompt_type === 'user')?.content || '',
      system_prompt_placeholders: validatedConfig.prompts?.find((p: any) => p.prompt_type === 'system')?.placeholders || {},
      user_prompt_placeholders: validatedConfig.prompts?.find((p: any) => p.prompt_type === 'user')?.placeholders || {},
    }));

    // Ensure tools are selected based on AI recommendation
    if (validatedConfig.tool_ids && validatedConfig.tool_ids.length > 0) {
      setSelectedTools(prev => prev.map(tool => ({
        ...tool,
        selected: validatedConfig.tool_ids!.includes(tool.id)
      })));
    }

    // Switch to manual mode with visual feedback
    setBuilderMode('manual');
    setFormHighlight(true);

    // Show additional toast after switching
    setTimeout(() => {
      showToast('Review your agent configuration and click Create!', 'info');
    }, 800);

    // Remove highlight after animation
    setTimeout(() => {
      setFormHighlight(false);
    }, 2000);
  };

  const handleSwitchToManual = () => {
    setBuilderMode('manual');
  };

  if (projectsLoading || toolsLoading) {
    return (
      <Layout>
        <LoadingState>Loading form data...</LoadingState>
      </Layout>
    );
  }

  return (
    <Layout fullHeight={builderMode === 'ai'}>
      <div className={builderMode === 'ai' ? 'flex flex-col h-[calc(100vh-80px)]' : 'mx-auto max-w-2xl'}>
        <div className={builderMode === 'ai' ? 'px-4 sm:px-6 lg:px-8 py-4 border-b border-[#374151] bg-[#1a2633]' : 'mb-8'}>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
                Create Agent
              </h1>
              <p className="text-gray-400 mt-1">
                {builderMode === 'ai'
                  ? 'Build your agent through an interactive conversation with AI.'
                  : 'Define and configure a new agent to assist with your tasks.'
                }
              </p>
            </div>
          </div>

          {/* Tab System */}
          <div className="mt-6">
            <div className="flex space-x-1 bg-[#111a22] p-1 rounded-lg">
              <button
                onClick={() => setBuilderMode('ai')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  builderMode === 'ai'
                    ? 'bg-[#1173d4] text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <span className="material-symbols-outlined text-base">smart_toy</span>
                AI Assistant
              </button>
              <button
                onClick={() => setBuilderMode('manual')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  builderMode === 'manual'
                    ? 'bg-[#1173d4] text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <span className="material-symbols-outlined text-base">edit</span>
                Manual Builder
              </button>
            </div>
          </div>
        </div>

        {/* AI Chat Interface */}
        {builderMode === 'ai' && (
          <div className="flex-1 min-h-0 p-4 sm:p-6 lg:p-8">
            <ChatInterface
              onAgentConfigComplete={handleAgentConfigComplete}
              onSwitchToManual={handleSwitchToManual}
              selectedProject={formData.project}
              onShowToast={showToast}
            />
          </div>
        )}

        {/* Manual Form Builder */}
        {builderMode === 'manual' && (
          <div className="mx-auto max-w-2xl px-4 sm:px-6 lg:px-8 py-8">

        <form onSubmit={handleSubmit} className={`space-y-8 transition-all duration-500 ${formHighlight ? 'ring-2 ring-[#1173d4] ring-opacity-50 shadow-lg shadow-[#1173d4]/20 rounded-lg p-6' : ''}`}>
          {/* Basic Information */}
          <div className="space-y-6">
            <Input
              label="Agent Name"
              placeholder="e.g., Customer Support Bot"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              required
            />

            <Select
              label="Project"
              value={formData.project}
              onChange={(e) => handleInputChange('project', parseInt(e.target.value))}
              options={[
                { value: 0, label: 'Select a project', disabled: true },
                ...(projects?.results?.map(p => ({ value: p.id, label: p.name })) || [])
              ]}
              required
            />

            <Textarea
              label="Agent Description"
              placeholder="Describe the agent's primary function or purpose. e.g., 'This agent will handle customer inquiries and provide product support.'"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              helperText="A clear description helps the agent perform better."
            />

            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Return Type"
                value={formData.return_type}
                onChange={(e) => handleInputChange('return_type', e.target.value as ReturnType)}
                options={[
                  { value: 'unstructured', label: 'Unstructured' },
                  { value: 'structured', label: 'Structured' },
                ]}
              />

              {formData.return_type === 'structured' && (
                <Textarea
                  label="JSON Schema"
                  placeholder='{"type": "object", "properties": {"intent": {"type": "string"}}}'
                  value={formData.schema_definition}
                  onChange={(e) => handleInputChange('schema_definition', e.target.value)}
                  error={schemaError}
                  helperText="Define the structure of the agent's response"
                  className="min-h-[100px]"
                />
              )}
            </div>
          </div>

          {/* Skills & Tools */}
          <div>
            <h2 className="text-white text-xl font-bold leading-tight tracking-tight mb-4">
              Skills & Tools
            </h2>
            <Card variant="border" className="p-4">
              <p className="text-gray-300 mb-4">
                Select the skills and tools this agent can use.
              </p>
              <div className="grid grid-cols-2 gap-4">
                {selectedTools.map((tool) => (
                  <div
                    key={tool.id}
                    className="flex items-center gap-3 rounded-md bg-[#233648] p-3"
                  >
                    <span className="material-symbols-outlined text-gray-400">
                      {getToolIcon(tool.tool_type)}
                    </span>
                    <span className="text-white text-sm flex-1">{tool.name}</span>
                    <button
                      type="button"
                      onClick={() => toggleTool(tool.id)}
                      className={`flex items-center justify-center h-6 w-6 rounded-full text-white transition-colors ${
                        tool.selected
                          ? 'bg-green-500 hover:bg-green-600'
                          : 'bg-[#1173d4] hover:bg-blue-600'
                      }`}
                    >
                      <span className="material-symbols-outlined text-sm">
                        {tool.selected ? 'check' : 'add'}
                      </span>
                    </button>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Custom Prompts */}
          <div>
            <h2 className="text-white text-xl font-bold leading-tight tracking-tight mb-4">
              Custom Prompts
            </h2>
            <div className="space-y-6">
              <Textarea
                label="System Prompt"
                placeholder="Enter the system-level instructions for the agent. This sets the context and constraints for its operation."
                value={formData.system_prompt}
                onChange={(e) => handleInputChange('system_prompt', e.target.value)}
                className="min-h-[150px]"
              />

              <Textarea
                label="User Prompt Example"
                placeholder="Provide an example of a typical user request to this agent."
                value={formData.user_prompt}
                onChange={(e) => handleInputChange('user_prompt', e.target.value)}
                className="min-h-[120px]"
                helperText="This helps in fine-tuning the agent's responses."
              />
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-md">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-4 pt-4 border-t border-[#233648]">
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate('/agents')}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={submitting}
              leftIcon={<span className="material-symbols-outlined text-base">auto_awesome</span>}
            >
              Create Agent
            </Button>
          </div>
        </form>
          </div>
        )}
      </div>

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </Layout>
  );
}