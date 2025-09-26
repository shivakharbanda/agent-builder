import React, { useState } from 'react';
import { Link } from 'react-router';
import type { Route } from './+types/projects';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { LoadingState, EmptyState } from '../components/ui/Loading';
import { useProjects, useFormSubmit } from '../hooks/useAPI';
import { api } from '../lib/api';
import { formatRelativeTime } from '../lib/utils';
import type { ProjectCreate } from '../lib/types';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Projects - Agent Builder" },
    { name: "description", content: "Manage your AI projects and their agents" },
  ];
}

export default function Projects() {
  const { data: projects, loading, refetch } = useProjects();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '' });

  const { loading: creating, error, submit, reset } = useFormSubmit(
    async (data: ProjectCreate) => {
      const project = await api.createProject(data);
      return project;
    }
  );

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await submit(newProject);
      setNewProject({ name: '', description: '' });
      setShowCreateForm(false);
      reset();
      refetch();
    } catch (err) {
      // Error handled by hook
    }
  };

  return (
    <Layout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
              Projects
            </h1>
            <p className="text-gray-400 mt-1">
              Organize your AI agents and workflows into projects.
            </p>
          </div>
          <Button
            onClick={() => setShowCreateForm(true)}
            leftIcon={<span className="material-symbols-outlined text-base">add</span>}
          >
            New Project
          </Button>
        </div>

        {/* Create Project Form */}
        {showCreateForm && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Create New Project</CardTitle>
              <CardDescription>
                Create a new project to organize your agents and workflows
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateProject} className="space-y-4">
                <Input
                  label="Project Name"
                  placeholder="e.g., Customer Service Automation"
                  value={newProject.name}
                  onChange={(e) => setNewProject(prev => ({ ...prev, name: e.target.value }))}
                  required
                />
                <Input
                  label="Description"
                  placeholder="Brief description of the project"
                  value={newProject.description}
                  onChange={(e) => setNewProject(prev => ({ ...prev, description: e.target.value }))}
                />

                {error && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-md">
                    <p className="text-red-400 text-sm">{error}</p>
                  </div>
                )}

                <div className="flex gap-3">
                  <Button type="submit" loading={creating}>
                    Create Project
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowCreateForm(false);
                      setNewProject({ name: '', description: '' });
                      reset();
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Projects List */}
        {loading ? (
          <LoadingState>Loading projects...</LoadingState>
        ) : !projects?.results?.length ? (
          <EmptyState
            title="No projects yet"
            description="Create your first project to start building AI agents and workflows"
            icon={
              <span className="material-symbols-outlined text-4xl">folder_open</span>
            }
            action={
              <Button
                onClick={() => setShowCreateForm(true)}
                leftIcon={<span className="material-symbols-outlined text-base">add</span>}
              >
                Create Your First Project
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.results.map((project) => (
              <Card key={project.id} className="hover:bg-[#1f2937] transition-colors">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <Link
                        to={`/projects/${project.id}`}
                        className="text-lg font-semibold text-white hover:text-[#1173d4] transition-colors"
                      >
                        {project.name}
                      </Link>
                      <p className="text-gray-400 text-sm mt-1 line-clamp-2">
                        {project.description || 'No description provided'}
                      </p>
                    </div>
                    <Badge status={project.is_active ? 'active' : 'draft'}>
                      {project.is_active ? 'Active' : 'Draft'}
                    </Badge>
                  </div>

                  <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">smart_toy</span>
                      <span>{project.agents_count || 0} agents</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">account_tree</span>
                      <span>{project.workflows_count || 0} workflows</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-[#233648] flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Created {formatRelativeTime(project.created_at)}
                    </span>
                    <div className="flex gap-2">
                      <Link to={`/agents/create?project=${project.id}`}>
                        <Button size="sm" variant="outline">
                          <span className="material-symbols-outlined text-sm">add</span>
                          Agent
                        </Button>
                      </Link>
                      <Link to={`/projects/${project.id}`}>
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
        {projects && projects.count > 20 && (
          <div className="mt-8 flex justify-center">
            <p className="text-gray-400 text-sm">
              Showing {projects.results.length} of {projects.count} projects
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}