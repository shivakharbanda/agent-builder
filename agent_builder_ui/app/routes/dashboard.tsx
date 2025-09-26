import React from 'react';
import { Link } from 'react-router';
import type { Route } from './+types/dashboard';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingState, EmptyState } from '../components/ui/Loading';
import { useProjects, useAgents, useWorkflows } from '../hooks/useAPI';
import { formatRelativeTime } from '../lib/utils';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Dashboard - Agent Builder" },
    { name: "description", content: "Overview of your AI agents, projects, and workflows" },
  ];
}

export default function Dashboard() {
  const { data: projects, loading: projectsLoading } = useProjects();
  const { data: agents, loading: agentsLoading } = useAgents();
  const { data: workflows, loading: workflowsLoading } = useWorkflows();

  return (
    <Layout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
            Dashboard
          </h1>
          <p className="text-gray-400 mt-1">
            Manage your AI agents, projects, and workflows from one place.
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-400">Projects</p>
                  <p className="text-2xl font-bold text-white">
                    {projectsLoading ? '-' : projects?.count || 0}
                  </p>
                </div>
                <span className="material-symbols-outlined text-2xl text-[#1173d4]">
                  folder
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-400">Agents</p>
                  <p className="text-2xl font-bold text-white">
                    {agentsLoading ? '-' : agents?.count || 0}
                  </p>
                </div>
                <span className="material-symbols-outlined text-2xl text-[#1173d4]">
                  smart_toy
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-400">Workflows</p>
                  <p className="text-2xl font-bold text-white">
                    {workflowsLoading ? '-' : workflows?.count || 0}
                  </p>
                </div>
                <span className="material-symbols-outlined text-2xl text-[#1173d4]">
                  account_tree
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-400">Active Workflows</p>
                  <p className="text-2xl font-bold text-white">
                    {workflowsLoading ? '-' : workflows?.results?.filter(w => w.status === 'active').length || 0}
                  </p>
                </div>
                <span className="material-symbols-outlined text-2xl text-green-500">
                  play_circle
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Projects */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Recent Projects</CardTitle>
                  <CardDescription>Your latest AI projects</CardDescription>
                </div>
                <Link to="/projects">
                  <Button variant="outline" size="sm">
                    View All
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {projectsLoading ? (
                <LoadingState>Loading projects...</LoadingState>
              ) : !projects?.results?.length ? (
                <EmptyState
                  title="No projects yet"
                  description="Create your first project to get started with building AI agents"
                  action={
                    <Link to="/projects">
                      <Button>
                        <span className="material-symbols-outlined text-base">add</span>
                        Create Project
                      </Button>
                    </Link>
                  }
                />
              ) : (
                <div className="space-y-4">
                  {projects.results.slice(0, 3).map((project) => (
                    <div
                      key={project.id}
                      className="flex items-center justify-between p-4 bg-[#233648] rounded-lg hover:bg-[#2e4359] transition-colors"
                    >
                      <div className="flex-1">
                        <Link
                          to={`/projects/${project.id}`}
                          className="text-white font-medium hover:text-[#1173d4] transition-colors"
                        >
                          {project.name}
                        </Link>
                        <p className="text-sm text-gray-400 mt-1">
                          {project.description || 'No description'}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                          <span>{project.agents_count || 0} agents</span>
                          <span>{project.workflows_count || 0} workflows</span>
                          <span>{formatRelativeTime(project.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Agents */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Recent Agents</CardTitle>
                  <CardDescription>Your latest AI agents</CardDescription>
                </div>
                <Link to="/agents">
                  <Button variant="outline" size="sm">
                    View All
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {agentsLoading ? (
                <LoadingState>Loading agents...</LoadingState>
              ) : !agents?.results?.length ? (
                <EmptyState
                  title="No agents yet"
                  description="Create your first AI agent to start automating tasks"
                  action={
                    <Link to="/agents/create">
                      <Button>
                        <span className="material-symbols-outlined text-base">auto_awesome</span>
                        Create Agent
                      </Button>
                    </Link>
                  }
                />
              ) : (
                <div className="space-y-4">
                  {agents.results.slice(0, 3).map((agent) => (
                    <div
                      key={agent.id}
                      className="flex items-center justify-between p-4 bg-[#233648] rounded-lg hover:bg-[#2e4359] transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/agents/${agent.id}`}
                            className="text-white font-medium hover:text-[#1173d4] transition-colors"
                          >
                            {agent.name}
                          </Link>
                          <Badge status={agent.return_type}>
                            {agent.return_type}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-400 mt-1">
                          {agent.description || 'No description'}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                          <span>{agent.project_name}</span>
                          <span>{agent.prompts_count || 0} prompts</span>
                          <span>{agent.tools_count || 0} tools</span>
                          <span>{formatRelativeTime(agent.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks to get you started</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Link to="/projects" className="block">
                <div className="p-4 bg-[#233648] rounded-lg hover:bg-[#2e4359] transition-colors text-center">
                  <span className="material-symbols-outlined text-3xl text-[#1173d4] mb-2 block">
                    add_circle
                  </span>
                  <h3 className="text-white font-medium">New Project</h3>
                  <p className="text-sm text-gray-400 mt-1">Create a new AI project</p>
                </div>
              </Link>

              <Link to="/agents/create" className="block">
                <div className="p-4 bg-[#233648] rounded-lg hover:bg-[#2e4359] transition-colors text-center">
                  <span className="material-symbols-outlined text-3xl text-[#1173d4] mb-2 block">
                    auto_awesome
                  </span>
                  <h3 className="text-white font-medium">New Agent</h3>
                  <p className="text-sm text-gray-400 mt-1">Build an AI agent</p>
                </div>
              </Link>

              <Link to="/workflows/create" className="block">
                <div className="p-4 bg-[#233648] rounded-lg hover:bg-[#2e4359] transition-colors text-center">
                  <span className="material-symbols-outlined text-3xl text-[#1173d4] mb-2 block">
                    account_tree
                  </span>
                  <h3 className="text-white font-medium">New Workflow</h3>
                  <p className="text-sm text-gray-400 mt-1">Create a workflow</p>
                </div>
              </Link>

              <Link to="/tools" className="block">
                <div className="p-4 bg-[#233648] rounded-lg hover:bg-[#2e4359] transition-colors text-center">
                  <span className="material-symbols-outlined text-3xl text-[#1173d4] mb-2 block">
                    extension
                  </span>
                  <h3 className="text-white font-medium">Tool Library</h3>
                  <p className="text-sm text-gray-400 mt-1">Browse available tools</p>
                </div>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}