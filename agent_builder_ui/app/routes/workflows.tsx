import React, { useState } from 'react';
import { Link } from 'react-router';
import type { Route } from './+types/workflows';
import { Layout } from '../components/layout/Layout';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingState, EmptyState } from '../components/ui/Loading';
import { APIErrorBoundary } from '../components/ui/ErrorBoundary';
import { useWorkflows } from '../hooks/useAPI';
import { formatRelativeTime } from '../lib/utils';
import { api } from '../lib/api';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Workflows - Agent Builder" },
    { name: "description", content: "Manage your AI workflows and automation pipelines" },
  ];
}

export default function Workflows() {
  const { data: workflows, loading, error, isConnected, retryCount, refetch } = useWorkflows();
  const [deleting, setDeleting] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<{ id: number; name: string } | null>(null);

  const handleDelete = async (workflowId: number) => {
    try {
      setDeleting(workflowId);
      await api.deleteWorkflow(workflowId);
      await refetch(); // Refresh the list
      setShowDeleteConfirm(null);
    } catch (error) {
      console.error('Failed to delete workflow:', error);
      // TODO: Show error toast notification
    } finally {
      setDeleting(null);
    }
  };

  return (
    <Layout>
      <APIErrorBoundary>
        <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
              Workflows
            </h1>
            <p className="text-gray-400 mt-1">
              Create and manage automated workflows with your AI agents.
            </p>
          </div>
          <Button
            asChild
            leftIcon={<span className="material-symbols-outlined text-base">account_tree</span>}
          >
            <Link to="/workflows/create">Create Workflow</Link>
          </Button>
        </div>

        {/* Workflows List */}
        {loading ? (
          <LoadingState>Loading workflows...</LoadingState>
        ) : !workflows?.results?.length ? (
          <EmptyState
            title="No workflows yet"
            description="Create your first workflow to automate tasks with your AI agents"
            icon={
              <span className="material-symbols-outlined text-4xl">account_tree</span>
            }
            action={
              <Button
                asChild
                leftIcon={<span className="material-symbols-outlined text-base">account_tree</span>}
              >
                <Link to="/workflows/create">Create Your First Workflow</Link>
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {workflows.results.map((workflow) => (
              <Card key={workflow.id} className="hover:bg-[#1f2937] transition-colors">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <Link
                        to={`/workflows/${workflow.id}`}
                        className="text-lg font-semibold text-white hover:text-[#1173d4] transition-colors"
                      >
                        {workflow.name}
                      </Link>
                      <p className="text-gray-400 text-sm mt-1 line-clamp-2">
                        {workflow.description || 'No description provided'}
                      </p>
                    </div>
                    <Badge status={workflow.status}>
                      {workflow.status}
                    </Badge>
                  </div>

                  <div className="mt-3">
                    <p className="text-xs text-gray-500">
                      Project: {workflow.project_name}
                    </p>
                  </div>

                  <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">hub</span>
                      <span>{workflow.nodes_count || 0} nodes</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-[#233648] flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Created {formatRelativeTime(workflow.created_at)}
                    </span>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" asChild>
                        <Link to={`/workflows/${workflow.id}/edit`}>
                          <span className="material-symbols-outlined text-sm">edit</span>
                          Edit
                        </Link>
                      </Button>
                      <Button size="sm" asChild>
                        <Link to={`/workflows/${workflow.id}`}>View</Link>
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => setShowDeleteConfirm({ id: workflow.id, name: workflow.name })}
                        disabled={deleting === workflow.id}
                        loading={deleting === workflow.id}
                      >
                        <span className="material-symbols-outlined text-sm">delete</span>
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Pagination */}
        {workflows && workflows.count > 20 && (
          <div className="mt-8 flex justify-center">
            <p className="text-gray-400 text-sm">
              Showing {workflows.results.length} of {workflows.count} workflows
            </p>
          </div>
        )}

        {/* Connection Status */}
        {!isConnected && (
          <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <div className="flex items-center gap-2 text-yellow-400 text-sm">
              <span className="material-symbols-outlined text-sm">cloud_off</span>
              <span>Offline mode - showing cached data</span>
              {retryCount > 0 && <span>• Retry attempt {retryCount}</span>}
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && isConnected && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <span className="material-symbols-outlined text-sm">error</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-[#1a2633] rounded-lg p-6 max-w-md w-full mx-4">
              <div className="flex items-center gap-3 mb-4">
                <span className="material-symbols-outlined text-red-400 text-2xl">warning</span>
                <h3 className="text-lg font-semibold text-white">Delete Workflow</h3>
              </div>

              <p className="text-gray-300 mb-6">
                Are you sure you want to delete <strong>{showDeleteConfirm.name}</strong>? This action cannot be undone.
                All workflow nodes, configurations, and execution history will be permanently removed.
              </p>

              <div className="flex gap-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirm(null)}
                  disabled={deleting !== null}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  onClick={() => handleDelete(showDeleteConfirm.id)}
                  loading={deleting === showDeleteConfirm.id}
                  leftIcon={<span className="material-symbols-outlined text-base">delete</span>}
                >
                  Delete Workflow
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
      </APIErrorBoundary>
    </Layout>
  );
}