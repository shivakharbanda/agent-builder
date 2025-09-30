import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import type { Route } from './+types/create';

import { Layout } from '../../components/layout/Layout';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { WorkflowCanvas } from '../../components/workflow/WorkflowCanvas';
import type { WorkflowConfig } from '../../components/workflow/types';
import { NodePalette } from '../../components/workflow/NodePalette';
import { ChatInterface } from '../../components/workflow/ChatInterface';
import { ConfigViewer } from '../../components/workflow/ConfigViewer';
import { WorkflowErrorBoundary } from '../../components/ui/ErrorBoundary';
import { useFormSubmit } from '../../hooks/useAPI';
import { api } from '../../lib/api';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Create Workflow - Agent Builder" },
    { name: "description", content: "Build AI workflows with visual node editor" },
  ];
}

export default function CreateWorkflow() {
  const navigate = useNavigate();
  const params = useParams();
  const isEditMode = Boolean(params.id);
  const [searchValue, setSearchValue] = useState('');
  const [workflowName, setWorkflowName] = useState('Untitled Workflow');
  const [workflowDescription, setWorkflowDescription] = useState('');
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
  const [showConfig, setShowConfig] = useState(false);
  const [isLoadingWorkflow, setIsLoadingWorkflow] = useState(isEditMode);

  // Form submission hook - use different API based on mode
  const { loading: saving, error: saveError, submit: submitWorkflow } = useFormSubmit(
    async (data: any) => {
      if (isEditMode) {
        return api.updateWorkflow(Number(params.id), data);
      } else {
        return api.saveCompleteWorkflow(data);
      }
    }
  );

  // Fetch workflow details if editing
  useEffect(() => {
    const workflowId = params.id;
    if (workflowId) {
      api.getWorkflow(Number(workflowId))
        .then(workflow => {
          console.log('Workflow details:', workflow);

          setIsLoadingWorkflow(true);

          // Map workflow data back to state
          setWorkflowName(workflow.name);
          setWorkflowDescription(workflow.description);

          // Fix properties mapping - properties is at root level, not in configuration
          setWorkflowConfig({
            nodes: workflow.configuration.nodes,
            edges: workflow.configuration.edges,
            metadata: workflow.configuration.metadata,
            properties: workflow.properties  // From root level!
          });

          // Brief delay to prevent recursive updates
          setTimeout(() => setIsLoadingWorkflow(false), 100);
        })
        .catch(error => {
          console.error('Error fetching workflow:', error);
        });
    }
  }, [params.id]);

  const handleConfigChange = (config: WorkflowConfig) => {
    if (isLoadingWorkflow) return; // Skip during initial load
    setWorkflowConfig(config);
  };

  const handleChatCommand = (command: string) => {
    // Handle chat commands here
    // You can extend this to parse commands and manipulate the workflow
  };

  const handleSaveWorkflow = async () => {
    try {
      // Validate workflow before saving
      if (!workflowName.trim()) {
        alert('Please enter a workflow name');
        return;
      }

      if (workflowConfig.nodes.length === 0) {
        alert('Please add at least one node to your workflow before saving');
        return;
      }

      // Prepare workflow data based on mode
      const workflowData = isEditMode ? {
        // Update API expects simpler structure
        name: workflowName,
        description: workflowDescription,
        configuration: {
          nodes: workflowConfig.nodes,
          edges: workflowConfig.edges,
          metadata: {
            ...workflowConfig.metadata,
            name: workflowName,
            description: workflowDescription,
            updated: new Date().toISOString()
          }
        }
      } : {
        // Create API expects full structure
        name: workflowName,
        description: workflowDescription,
        project: 1, // TODO: Get from context or user selection
        configuration: {
          nodes: workflowConfig.nodes,
          edges: workflowConfig.edges,
          metadata: {
            ...workflowConfig.metadata,
            name: workflowName,
            description: workflowDescription,
            updated: new Date().toISOString()
          }
        },
        properties: workflowConfig.properties
      };

      // API call (create or update)
      const savedWorkflow = await submitWorkflow(workflowData);

      // Navigate based on mode
      if (isEditMode) {
        // Stay on edit page or go to view page
        navigate(`/workflows/${savedWorkflow.id}`);
      } else {
        // Go to view page after create
        navigate(`/workflows/${savedWorkflow.id}`);
      }
    } catch (error) {
      // Error is handled by useFormSubmit hook and displayed in UI
    }
  };

  return (
    <Layout fullHeight={true}>
      <div className="flex flex-col min-h-[calc(100vh-80px)] h-[calc(100vh-80px)]">
        {/* Header */}
        <div className="px-4 sm:px-6 lg:px-8 py-4 border-b border-[#374151] bg-[#1a2633]">
          <div className="flex items-center justify-between">
            <div className="flex-1 max-w-2xl">
              <div className="flex items-center gap-4 mb-3">
                <Input
                  type="text"
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  className="text-2xl font-bold bg-transparent border-none focus:ring-1 focus:ring-[#1173d4] text-white placeholder-gray-500 p-0 h-auto"
                  placeholder="Enter workflow name..."
                />
              </div>
              <div className="flex items-center gap-4">
                <Input
                  type="text"
                  value={workflowDescription}
                  onChange={(e) => setWorkflowDescription(e.target.value)}
                  className="bg-transparent border-none focus:ring-1 focus:ring-[#1173d4] text-gray-400 placeholder-gray-500 p-0 h-auto text-sm"
                  placeholder="Add a description for your workflow..."
                />
                {workflowConfig.nodes.length > 0 && (
                  <span className="text-sm text-gray-500 whitespace-nowrap">
                    • {workflowConfig.nodes.length} nodes, {workflowConfig.edges.length} connections
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {saveError && (
                <div className="text-red-400 text-sm mr-2">
                  Save failed: {saveError}
                </div>
              )}
              <Button variant="outline" asChild disabled={saving}>
                <Link to="/workflows">Cancel</Link>
              </Button>
              <Button onClick={handleSaveWorkflow} disabled={saving}>
                {saving ? (
                  <>
                    <span className="material-symbols-outlined text-sm mr-1 animate-spin">progress_activity</span>
                    {isEditMode ? 'Updating...' : 'Saving...'}
                  </>
                ) : (
                  isEditMode ? 'Update Workflow' : 'Save Workflow'
                )}
              </Button>
            </div>
          </div>
        </div>

        <div className="flex-grow flex overflow-hidden relative">
          {/* Sidebar */}
          <aside className="w-80 sm:w-96 flex flex-col border-r border-[#374151] bg-[#1a2633] z-10">
            {/* Search */}
            <div className="p-4 border-b border-[#374151]">
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                  search
                </span>
                <Input
                  type="text"
                  placeholder="Search nodes..."
                  value={searchValue}
                  onChange={(e) => setSearchValue(e.target.value)}
                  className="w-full bg-[#111a22] border border-[#374151] rounded-md pl-10 pr-4 py-2 focus:ring-[#1173d4] focus:border-[#1173d4] text-sm text-white"
                />
              </div>
            </div>

            {/* Node Palette */}
            <div className="flex-grow overflow-y-auto p-4">
              <NodePalette />
            </div>

            {/* Chat Interface */}
            <ChatInterface onCommand={handleChatCommand} />
          </aside>

          {/* Main Canvas */}
          <main className="flex-grow bg-[#111a22] relative">
            <WorkflowErrorBoundary>
              <WorkflowCanvas onConfigChange={handleConfigChange} initialConfig={workflowConfig} isLoading={isLoadingWorkflow} />
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
    </Layout>
  );
}