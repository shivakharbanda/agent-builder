import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import type { Route } from './+types/$id';
import { Layout } from '../../components/layout/Layout';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { LoadingState } from '../../components/ui/Loading';
import { useAgent, useAgentPrompts, useAgentTools } from '../../hooks/useAPI';
import { api } from '../../lib/api';
import { formatRelativeTime } from '../../lib/utils';

export function meta({ params }: Route.MetaArgs) {
  return [
    { title: `Agent ${params.id} - Agent Builder` },
    { name: "description", content: "View and manage agent details" },
  ];
}

export default function AgentDetail() {
  const params = useParams();
  const navigate = useNavigate();
  const agentId = parseInt(params.id);

  const { data: agent, loading: agentLoading } = useAgent(agentId);
  const { data: prompts, loading: promptsLoading } = useAgentPrompts(agentId);
  const { data: tools, loading: toolsLoading } = useAgentTools(agentId);

  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleDelete = async () => {
    try {
      setDeleting(true);
      await api.deleteAgent(agentId);
      navigate('/agents');
    } catch (error) {
      console.error('Failed to delete agent:', error);
      // TODO: Show error toast
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  if (agentLoading) {
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
      <div className="mx-auto max-w-4xl">
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
            <span>{agent.name}</span>
          </div>

          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
                {agent.name}
              </h1>
              <p className="text-gray-400 mt-1">
                {agent.description || 'No description provided'}
              </p>
              <div className="flex items-center gap-4 mt-3">
                <Badge status={agent.return_type}>
                  {agent.return_type}
                </Badge>
                <span className="text-sm text-gray-500">
                  Project: {agent.project_name}
                </span>
                <span className="text-sm text-gray-500">
                  Created {formatRelativeTime(agent.created_at)}
                </span>
              </div>
            </div>

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => navigate(`/agents/${agentId}/edit`)}
                leftIcon={<span className="material-symbols-outlined text-base">edit</span>}
              >
                Edit
              </Button>
              <Button
                variant="outline"
                color="red"
                onClick={() => setShowDeleteConfirm(true)}
                leftIcon={<span className="material-symbols-outlined text-base">delete</span>}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Schema Definition */}
          {agent.return_type === 'structured' && agent.schema_definition && (
            <Card className="lg:col-span-2">
              <CardContent className="pt-6">
                <h3 className="text-lg font-semibold text-white mb-4">Schema Definition</h3>
                <div className="bg-[#111a22] rounded-md p-4 overflow-auto">
                  <pre className="text-sm text-gray-300">
                    {JSON.stringify(agent.schema_definition, null, 2)}
                  </pre>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Prompts */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Prompts</h3>
                <Badge variant="secondary">{prompts?.length || 0}</Badge>
              </div>

              {promptsLoading ? (
                <div className="text-center py-4">
                  <div className="text-gray-400">Loading prompts...</div>
                </div>
              ) : !prompts?.length ? (
                <div className="text-center py-4">
                  <span className="material-symbols-outlined text-2xl text-gray-500 mb-2">chat</span>
                  <p className="text-gray-500 text-sm">No prompts configured</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {prompts.map((prompt) => (
                    <div key={prompt.id} className="bg-[#111a22] rounded-md p-3">
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="outline" size="sm">
                          {prompt.prompt_type}
                        </Badge>
                      </div>
                      <p className="text-gray-300 text-sm line-clamp-3">
                        {prompt.content}
                      </p>
                      {Object.keys(prompt.placeholders).length > 0 && (
                        <div className="mt-2 text-xs text-gray-500">
                          Placeholders: {Object.keys(prompt.placeholders).join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tools */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Tools</h3>
                <Badge variant="secondary">{tools?.length || 0}</Badge>
              </div>

              {toolsLoading ? (
                <div className="text-center py-4">
                  <div className="text-gray-400">Loading tools...</div>
                </div>
              ) : !tools?.length ? (
                <div className="text-center py-4">
                  <span className="material-symbols-outlined text-2xl text-gray-500 mb-2">extension</span>
                  <p className="text-gray-500 text-sm">No tools configured</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {tools.map((tool) => (
                    <div key={tool.id} className="bg-[#111a22] rounded-md p-3">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-sm text-gray-400">extension</span>
                        <span className="text-white text-sm font-medium">{tool.tool_name}</span>
                        <Badge variant="outline" size="sm">{tool.tool_type}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-[#1a2633] rounded-lg p-6 max-w-md w-full mx-4">
              <div className="flex items-center gap-3 mb-4">
                <span className="material-symbols-outlined text-red-400 text-2xl">warning</span>
                <h3 className="text-lg font-semibold text-white">Delete Agent</h3>
              </div>

              <p className="text-gray-300 mb-6">
                Are you sure you want to delete <strong>{agent.name}</strong>? This action cannot be undone.
              </p>

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                >
                  Cancel
                </Button>
                <Button
                  color="red"
                  onClick={handleDelete}
                  loading={deleting}
                  leftIcon={<span className="material-symbols-outlined text-base">delete</span>}
                >
                  Delete Agent
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}