import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router';
import type { Route } from './+types/$id';
import { Layout } from '../../components/layout/Layout';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { LoadingState } from '../../components/ui/Loading';
import { APIErrorBoundary } from '../../components/ui/ErrorBoundary';
import { useWorkflow } from '../../hooks/useAPI';
import { formatRelativeTime } from '../../lib/utils';
import { api } from '../../lib/api';

// Simple React Flow Canvas for viewing only
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  Handle,
  Position,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export function meta({ params }: Route.MetaArgs) {
  return [
    { title: `Workflow ${params.id} - Agent Builder` },
    { name: "description", content: "View AI workflow details" },
  ];
}

// Simple node components for viewing
function SimpleNode({ data, selected }: { data: any; selected: boolean }) {
  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'database': return 'storage';
      case 'agent': return 'smart_toy';
      case 'output': return 'save';
      default: return 'hub';
    }
  };

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'database': return '#10b981';
      case 'agent': return '#3b82f6';
      case 'output': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  return (
    <div
      className={`bg-[#1a2633] p-4 rounded-lg shadow-md border-2 w-48 transition-all ${
        selected ? 'border-[#1173d4] shadow-lg shadow-[#1173d4]/20' : 'border-[#374151]'
      }`}
      style={{ borderColor: selected ? '#1173d4' : getNodeColor(data.type) }}
    >
      <div className="flex items-center mb-2">
        <span
          className="material-symbols-outlined mr-2 text-xl"
          style={{ color: getNodeColor(data.type) }}
        >
          {getNodeIcon(data.type)}
        </span>
        <h4 className="font-semibold text-white text-sm">{data.label}</h4>
      </div>
      <p className="text-xs text-gray-400 mb-2">{data.description}</p>
      {data.configured && (
        <div className="text-xs text-green-400">✓ Configured</div>
      )}

      {/* Input Handle - only for agent and output nodes */}
      {(data.type === 'agent' || data.type === 'output') && (
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
        />
      )}

      {/* Output Handle - only for database and agent nodes */}
      {(data.type === 'database' || data.type === 'agent') && (
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 bg-[#1173d4] border-2 border-[#1a2633]"
        />
      )}
    </div>
  );
}

const nodeTypes = {
  database: SimpleNode,
  agent: SimpleNode,
  output: SimpleNode,
  default: SimpleNode,
};

export default function WorkflowDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const workflowId = parseInt(id || '0');
  const { data: workflow, loading, error, isConnected, refetch } = useWorkflow(workflowId);

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleDelete = async () => {
    try {
      setDeleting(true);
      await api.deleteWorkflow(workflowId);
      navigate('/workflows');
    } catch (error) {
      console.error('Failed to delete workflow:', error);
      // TODO: Show error toast notification
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  // Convert workflow data to React Flow format
  useEffect(() => {
    if (!workflow || !workflow.nodes) {
      setNodes([]);
      setEdges([]);
      return;
    }


    // Map backend node types to frontend types
    const mapNodeType = (backendType: string): string => {
      switch (backendType) {
        case 'input': return 'database';
        case 'database': return 'database'; // Handle direct database type
        case 'agent': return 'agent';
        case 'output': return 'output';
        default: return 'default';
      }
    };

    // Helper function to find matching config node ID for backend node
    const getConfigNodeId = (backendNode: any): string | null => {
      const configNodes = workflow.configuration?.nodes || [];
      // Match by position in the array (backend nodes are ordered by position)
      const configNode = configNodes[backendNode.position];
      return configNode?.id || null;
    };

    // Convert nodes
    const flowNodes: Node[] = workflow.nodes.map((node) => {
      const configNodeId = getConfigNodeId(node);
      const nodeId = configNodeId || node.id.toString();

      return {
        id: nodeId,
        type: mapNodeType(node.node_type),
        position: node.visual_position || { x: 100, y: 100 },
        data: {
          label: `${node.node_type.charAt(0).toUpperCase()}${node.node_type.slice(1)} Node`,
          type: mapNodeType(node.node_type),
          description: getNodeDescription(node.node_type),
          configured: Object.keys(node.configuration || {}).length > 0,
          config: node.configuration
        },
        draggable: false,
        selectable: true,
      };
    });

    // Convert edges from configuration
    const flowEdges: Edge[] = (workflow.configuration?.edges || []).map((edge: any) => {
      return {
        id: edge.id || `${edge.source}-${edge.target}`,
        source: edge.source.toString(), // Ensure string type
        target: edge.target.toString(), // Ensure string type
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#1173d4', strokeWidth: 2 },
      };
    });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [workflow]);

  const getNodeDescription = (nodeType: string): string => {
    switch (nodeType) {
      case 'input': return 'Data input source';
      case 'agent': return 'AI processing agent';
      case 'output': return 'Data output destination';
      default: return 'Workflow node';
    }
  };

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
                  <Badge status={workflow?.current_execution?.status || 'draft'}>
                    {workflow?.current_execution?.status || 'draft'}
                  </Badge>
                </div>
                <p className="text-gray-400 ml-11">
                  {workflow?.description || 'No description provided'}
                  {workflow && (
                    <span className="ml-4 text-sm">
                      • Created {formatRelativeTime(workflow.created_at)}
                      • {workflow.nodes?.length || 0} nodes
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
                <Button
                  variant="danger"
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={deleting}
                  leftIcon={<span className="material-symbols-outlined text-base">delete</span>}
                >
                  Delete
                </Button>
                <Button>Run Workflow</Button>
              </div>
            </div>
          </div>

          {/* Error Status */}
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

          {/* Workflow Canvas */}
          <div className="flex-grow bg-[#111a22] relative">
            <div className="w-full h-full">
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                className="bg-[#111a22]"
                connectionLineStyle={{ stroke: '#1173d4', strokeWidth: 2 }}
                defaultEdgeOptions={{
                  style: { stroke: '#1173d4', strokeWidth: 2 },
                  type: 'smoothstep',
                  animated: true,
                }}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={true}
                selectNodesOnDrag={false}
                fitView
                fitViewOptions={{
                  padding: 0.2,
                  minZoom: 0.1,
                  maxZoom: 2
                }}
                minZoom={0.1}
                maxZoom={2}
                defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
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
                  position="bottom-right"
                />
                <MiniMap
                  className="bg-[#1a2633] border border-[#374151]"
                  nodeColor="#1173d4"
                  nodeStrokeColor="#374151"
                  nodeStrokeWidth={1}
                  maskColor="rgba(26, 38, 51, 0.8)"
                />
              </ReactFlow>

              {/* View Mode Indicator */}
              <div className="absolute top-4 left-4 bg-[#1a2633] border border-[#374151] rounded-lg px-3 py-2 text-sm text-gray-400">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm">visibility</span>
                  <span>View Mode</span>
                </div>
              </div>

              {/* Empty State */}
              {nodes.length === 0 && !loading && (
                <div className="absolute inset-0 flex items-center justify-center opacity-70 pointer-events-none z-10">
                  <div className="text-center p-8 border-2 border-dashed border-[#374151] rounded-lg bg-[#111a22]/80 backdrop-blur-sm max-w-md">
                    <span className="material-symbols-outlined text-6xl text-gray-400 mb-4 block">account_tree</span>
                    <h3 className="text-white text-lg font-semibold mb-2">No Workflow Nodes</h3>
                    <p className="text-gray-400 mb-4">
                      This workflow doesn't have any nodes configured yet.
                    </p>
                    <Button variant="outline" asChild>
                      <Link to={`/workflows/${id}/edit`}>Edit Workflow</Link>
                    </Button>
                  </div>
                </div>
              )}

              {/* Debug Info (Development Only) */}
              {process.env.NODE_ENV === 'development' && (
                <div className="absolute top-16 left-4 bg-[#1a2633] border border-[#374151] rounded-lg px-3 py-2 text-xs text-gray-500 max-w-xs">
                  <p>Nodes: {nodes.length}</p>
                  <p>Edges: {edges.length}</p>
                  <p>Loading: {loading ? 'true' : 'false'}</p>
                  <p>Error: {error ? 'true' : 'false'}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-[#1a2633] rounded-lg p-6 max-w-md w-full mx-4">
              <div className="flex items-center gap-3 mb-4">
                <span className="material-symbols-outlined text-red-400 text-2xl">warning</span>
                <h3 className="text-lg font-semibold text-white">Delete Workflow</h3>
              </div>

              <p className="text-gray-300 mb-6">
                Are you sure you want to delete <strong>{workflow?.name}</strong>? This action cannot be undone.
                All workflow nodes, configurations, and execution history will be permanently removed.
              </p>

              <div className="flex gap-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  onClick={handleDelete}
                  loading={deleting}
                  leftIcon={<span className="material-symbols-outlined text-base">delete</span>}
                >
                  Delete Workflow
                </Button>
              </div>
            </div>
          </div>
        )}
      </APIErrorBoundary>
    </Layout>
  );
}