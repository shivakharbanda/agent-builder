import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router';
import type { Route } from './+types/$id.edit';
import { Layout } from '../../components/layout/Layout';
import { Input, Textarea, Select } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { LoadingState } from '../../components/ui/Loading';
import { useAgent, useProjects, useFormSubmit } from '../../hooks/useAPI';
import { api } from '../../lib/api';
import type { AgentCreate, ReturnType } from '../../lib/types';
import { isValidJSON } from '../../lib/utils';

export function meta({ params }: Route.MetaArgs) {
  return [
    { title: `Edit Agent ${params.id} - Agent Builder` },
    { name: "description", content: "Edit agent configuration" },
  ];
}

interface FormData {
  name: string;
  description: string;
  return_type: ReturnType;
  schema_definition: string;
}

export default function EditAgent() {
  const params = useParams();
  const navigate = useNavigate();
  const agentId = parseInt(params.id);

  const { data: agent, loading: agentLoading } = useAgent(agentId);
  const { data: projects, loading: projectsLoading } = useProjects();

  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    return_type: 'unstructured',
    schema_definition: '',
  });

  const [schemaError, setSchemaError] = useState<string>('');

  const { loading: submitting, error, submit } = useFormSubmit(
    async (data: FormData) => {
      const agentData: Partial<AgentCreate> = {
        name: data.name,
        description: data.description,
        return_type: data.return_type,
        schema_definition: data.return_type === 'structured' && data.schema_definition
          ? JSON.parse(data.schema_definition)
          : undefined,
      };

      const updatedAgent = await api.updateAgent(agentId, agentData);
      return updatedAgent;
    }
  );

  // Initialize form data when agent loads
  useEffect(() => {
    if (agent) {
      setFormData({
        name: agent.name,
        description: agent.description,
        return_type: agent.return_type,
        schema_definition: agent.schema_definition
          ? JSON.stringify(agent.schema_definition, null, 2)
          : '',
      });
    }
  }, [agent]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required fields
    if (!formData.name.trim()) {
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
      await submit(formData);
      navigate(`/agents/${agentId}`);
    } catch (err) {
      // Error is handled by the hook
    }
  };

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));

    if (field === 'schema_definition') {
      setSchemaError('');
    }
  };

  if (agentLoading || projectsLoading) {
    return (
      <Layout>
        <LoadingState>Loading agent details...</LoadingState>
      </Layout>
    );
  }

  if (!agent) {
    return (
      <Layout>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white">Agent not found</h1>
          <p className="text-gray-400 mt-2">The agent you're looking for doesn't exist.</p>
          <Button onClick={() => navigate('/agents')} className="mt-4">
            Back to Agents
          </Button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
            <button
              onClick={() => navigate('/agents')}
              className="hover:text-white transition-colors"
            >
              Agents
            </button>
            <span className="material-symbols-outlined text-sm">chevron_right</span>
            <button
              onClick={() => navigate(`/agents/${agentId}`)}
              className="hover:text-white transition-colors"
            >
              {agent.name}
            </button>
            <span className="material-symbols-outlined text-sm">chevron_right</span>
            <span>Edit</span>
          </div>

          <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
            Edit Agent
          </h1>
          <p className="text-gray-400 mt-1">
            Update the agent's configuration and settings.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Basic Information */}
          <Card variant="border" className="p-6">
            <h2 className="text-white text-xl font-bold leading-tight tracking-tight mb-6">
              Basic Information
            </h2>

            <div className="space-y-6">
              <Input
                label="Agent Name"
                placeholder="e.g., Customer Support Bot"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                required
              />

              <Textarea
                label="Agent Description"
                placeholder="Describe the agent's primary function or purpose."
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
                  <div className="col-span-2">
                    <Textarea
                      label="JSON Schema"
                      placeholder='{"type": "object", "properties": {"intent": {"type": "string"}}}'
                      value={formData.schema_definition}
                      onChange={(e) => handleInputChange('schema_definition', e.target.value)}
                      error={schemaError}
                      helperText="Define the structure of the agent's response"
                      className="min-h-[200px] font-mono text-sm"
                    />
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Project Info (Read-only) */}
          <Card variant="border" className="p-6">
            <h2 className="text-white text-xl font-bold leading-tight tracking-tight mb-4">
              Project
            </h2>
            <div className="bg-[#111a22] rounded-md p-4">
              <p className="text-gray-300">
                <span className="text-gray-500">Current project:</span> {agent.project_name}
              </p>
              <p className="text-gray-500 text-sm mt-1">
                Project assignment cannot be changed after creation.
              </p>
            </div>
          </Card>

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
              onClick={() => navigate(`/agents/${agentId}`)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={submitting}
              leftIcon={<span className="material-symbols-outlined text-base">save</span>}
            >
              Save Changes
            </Button>
          </div>
        </form>
      </div>
    </Layout>
  );
}