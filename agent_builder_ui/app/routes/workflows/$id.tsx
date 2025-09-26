import React from 'react';
import { Link, useParams } from 'react-router';
import type { Route } from './+types/$id';
import { Layout } from '../../components/layout/Layout';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { LoadingState } from '../../components/ui/Loading';
import { APIErrorBoundary, WorkflowErrorBoundary } from '../../components/ui/ErrorBoundary';
import { WorkflowCanvas } from '../../components/workflow/WorkflowCanvas';
import { ConfigViewer } from '../../components/workflow/ConfigViewer';
import { useWorkflow } from '../../hooks/useAPI';
import { formatRelativeTime } from '../../lib/utils';
import type { WorkflowConfig } from '../../components/workflow/types';

export function meta({ params }: Route.MetaArgs) {
  return [
    { title: `Workflow ${params.id} - Agent Builder` },
    { name: "description", content: "View and edit AI workflow details" },
  ];
}

export default function WorkflowDetail() {
  const { id } = useParams();
  const workflowId = parseInt(id || '0');
  const { data: workflow, loading, error, isConnected, refetch } = useWorkflow(workflowId);
  const [showConfig, setShowConfig] = React.useState(false);
  const [workflowConfig, setWorkflowConfig] = React.useState<WorkflowConfig>({
    nodes: [],
    edges: [],
    metadata: {
      name: 'Loading...',
      description: '',
      version: '1.0.0',
      created: new Date().toISOString(),
      updated: new Date().toISOString(),
    }
  });

  React.useEffect(() => {
    if (workflow) {
      setWorkflowConfig({
        nodes: workflow.nodes?.map(node => ({
          id: node.id.toString(),
          type: node.node_type,
          position: { x: 0, y: 0 }, // Would need to store position in backend
          config: node.configuration || {}
        })) || [],
        edges: [], // Would need to store edges in backend
        metadata: {
          name: workflow.name,
          description: workflow.description,
          version: '1.0.0',
          created: workflow.created_at,
          updated: workflow.updated_at,
        }
      });
    }
  }, [workflow]);

  if (loading) {
    return (
      <Layout>
        <LoadingState>Loading workflow details...</LoadingState>
      </Layout>
    );
  }

  if (error && !workflow) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6 max-w-md">
            <span className="material-symbols-outlined text-4xl text-red-400 mb-4 block">error</span>
            <h2 className="text-lg font-semibold text-white mb-2">Workflow Not Found</h2>
            <p className="text-gray-400 mb-4">{error}</p>
            <div className="flex gap-2 mt-4">
              <Button variant="outline" size="sm" onClick={refetch}>
                Retry
              </Button>
              <Button size="sm" asChild>
                <Link to="/workflows">Back to Workflows</Link>
              </Button>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout fullHeight={true}>
      <APIErrorBoundary>
        <div className="min-h-[calc(100vh-80px)] h-[calc(100vh-80px)] flex flex-col">
          {/* Header */}
          <div className="px-4 sm:px-6 lg:px-8 py-4 border-b border-[#374151] bg-[#1a2633]">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <Link
                    to="/workflows"
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <span className="material-symbols-outlined">arrow_back</span>
                  </Link>
                  <h1 className="text-white text-2xl font-bold">{workflow?.name}</h1>
                  <Badge status={workflow?.status || 'draft'}>
                    {workflow?.status || 'draft'}
                  </Badge>
                </div>
                <p className="text-gray-400 ml-11">
                  {workflow?.description || 'No description provided'}
                  {workflow && (
                    <span className="ml-4 text-sm">
                      • Created {formatRelativeTime(workflow.created_at)}
                      • {workflow.nodes_count || 0} nodes
                    </span>
                  )}
                </p>
              </div>
              <div className="flex items-center space-x-3">
                {!isConnected && (
                  <div className="flex items-center gap-2 text-yellow-400 text-sm">
                    <span className="material-symbols-outlined text-sm">cloud_off</span>
                    <span>Offline</span>
                  </div>
                )}
                <Button variant="outline" size="sm" onClick={refetch}>
                  <span className="material-symbols-outlined text-sm mr-1">refresh</span>
                  Refresh
                </Button>
                <Button variant="outline" asChild>
                  <Link to={`/workflows/${id}/edit`}>Edit Workflow</Link>
                </Button>
                <Button>Run Workflow</Button>
              </div>
            </div>
          </div>

          {/* Connection/Error Status */}
          {error && (
            <div className="px-4 sm:px-6 lg:px-8 py-2">
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <div className="flex items-center gap-2 text-red-400 text-sm">
                  <span className="material-symbols-outlined text-sm">error</span>
                  <span>{error}</span>
                </div>
              </div>
            </div>
          )}

          {/* Main Content */}
          <div className="flex-grow flex overflow-hidden relative">
            {/* Workflow Canvas - Read Only */}
            <main className="flex-grow bg-[#111a22] relative">
              <WorkflowErrorBoundary>
                <div className="w-full h-full relative">
                  <WorkflowCanvas
                    onConfigChange={setWorkflowConfig}
                  />

                  {/* Read-only overlay */}
                  <div className="absolute top-4 left-4 bg-[#1a2633] border border-[#374151] rounded-lg px-3 py-2 text-sm text-gray-400">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-sm">visibility</span>
                      <span>View Mode</span>
                    </div>
                  </div>
                </div>
              </WorkflowErrorBoundary>
            </main>

            {/* Config Viewer */}
            <ConfigViewer
              config={workflowConfig}
              isVisible={showConfig}
              onToggle={() => setShowConfig(!showConfig)}
            />
          </div>
        </div>
      </APIErrorBoundary>
    </Layout>
  );
}