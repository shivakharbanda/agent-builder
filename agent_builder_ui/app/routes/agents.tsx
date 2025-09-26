import React, { useState } from 'react';
import { Link } from 'react-router';
import type { Route } from './+types/agents';
import { Layout } from '../components/layout/Layout';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingState, EmptyState } from '../components/ui/Loading';
import { useAgents } from '../hooks/useAPI';
import { api } from '../lib/api';
import { formatRelativeTime } from '../lib/utils';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Agents - Agent Builder" },
    { name: "description", content: "Manage your AI agents and their configurations" },
  ];
}

export default function Agents() {
  const { data: agents, loading, refetch } = useAgents();
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (agentId: number, agentName: string) => {
    if (!confirm(`Are you sure you want to delete "${agentName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeleting(true);
      setDeleteId(agentId);
      await api.deleteAgent(agentId);
      await refetch(); // Refresh the list
    } catch (error) {
      console.error('Failed to delete agent:', error);
      // TODO: Show error toast
    } finally {
      setDeleting(false);
      setDeleteId(null);
    }
  };

  return (
    <Layout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
              Agents
            </h1>
            <p className="text-gray-400 mt-1">
              Build and manage your AI agents with custom prompts and tools.
            </p>
          </div>
          <Link to="/agents/create">
            <Button
              leftIcon={<span className="material-symbols-outlined text-base">auto_awesome</span>}
            >
              Create Agent
            </Button>
          </Link>
        </div>

        {/* Agents List */}
        {loading ? (
          <LoadingState>Loading agents...</LoadingState>
        ) : !agents?.results?.length ? (
          <EmptyState
            title="No agents yet"
            description="Create your first AI agent to start automating tasks and workflows"
            icon={
              <span className="material-symbols-outlined text-4xl">smart_toy</span>
            }
            action={
              <Link to="/agents/create">
                <Button
                  leftIcon={<span className="material-symbols-outlined text-base">auto_awesome</span>}
                >
                  Create Your First Agent
                </Button>
              </Link>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.results.map((agent) => (
              <Card key={agent.id} className="hover:bg-[#1f2937] transition-colors">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <Link
                        to={`/agents/${agent.id}`}
                        className="text-lg font-semibold text-white hover:text-[#1173d4] transition-colors"
                      >
                        {agent.name}
                      </Link>
                      <p className="text-gray-400 text-sm mt-1 line-clamp-2">
                        {agent.description || 'No description provided'}
                      </p>
                    </div>
                    <Badge status={agent.return_type}>
                      {agent.return_type}
                    </Badge>
                  </div>

                  <div className="mt-3">
                    <p className="text-xs text-gray-500">
                      Project: {agent.project_name}
                    </p>
                  </div>

                  <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">chat</span>
                      <span>{agent.prompts_count || 0} prompts</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">extension</span>
                      <span>{agent.tools_count || 0} tools</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-[#233648] flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Created {formatRelativeTime(agent.created_at)}
                    </span>
                    <div className="flex gap-2">
                      <Link to={`/agents/${agent.id}/edit`}>
                        <Button size="sm" variant="outline">
                          <span className="material-symbols-outlined text-sm">edit</span>
                          Edit
                        </Button>
                      </Link>
                      <Button
                        size="sm"
                        variant="outline"
                        color="red"
                        onClick={() => handleDelete(agent.id, agent.name)}
                        loading={deleting && deleteId === agent.id}
                        disabled={deleting}
                      >
                        <span className="material-symbols-outlined text-sm">delete</span>
                      </Button>
                      <Link to={`/agents/${agent.id}`}>
                        <Button size="sm">
                          View
                        </Button>
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Pagination */}
        {agents && agents.count > 20 && (
          <div className="mt-8 flex justify-center">
            <p className="text-gray-400 text-sm">
              Showing {agents.results.length} of {agents.count} agents
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}