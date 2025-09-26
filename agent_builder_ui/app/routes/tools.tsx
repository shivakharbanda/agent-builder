import React from 'react';
import type { Route } from './+types/tools';
import { Layout } from '../components/layout/Layout';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingState, EmptyState } from '../components/ui/Loading';
import { useTools } from '../hooks/useAPI';
import { formatRelativeTime } from '../lib/utils';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Tools - Agent Builder" },
    { name: "description", content: "Browse and manage available tools for your AI agents" },
  ];
}

export default function Tools() {
  const { data: tools, loading } = useTools();

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

  return (
    <Layout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
            Tool Library
          </h1>
          <p className="text-gray-400 mt-1">
            Browse available tools that your AI agents can use to perform tasks.
          </p>
        </div>

        {/* Tools List */}
        {loading ? (
          <LoadingState>Loading tools...</LoadingState>
        ) : !tools?.results?.length ? (
          <EmptyState
            title="No tools available"
            description="Tools will appear here when they are added to the system"
            icon={
              <span className="material-symbols-outlined text-4xl">extension</span>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tools.results.map((tool) => (
              <Card key={tool.id} className="hover:bg-[#1f2937] transition-colors">
                <CardContent className="pt-6">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0">
                      <div className="w-12 h-12 bg-[#1173d4]/10 rounded-lg flex items-center justify-center">
                        <span className="material-symbols-outlined text-2xl text-[#1173d4]">
                          {getToolIcon(tool.tool_type)}
                        </span>
                      </div>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-white">
                        {tool.name}
                      </h3>
                      <p className="text-gray-400 text-sm mt-1 line-clamp-2">
                        {tool.description || 'No description provided'}
                      </p>
                      <div className="mt-3">
                        <Badge variant="secondary">
                          {tool.tool_type}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-[#233648] flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Added {formatRelativeTime(tool.created_at)}
                    </span>
                    <Button size="sm" variant="outline">
                      View Details
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Pagination */}
        {tools && tools.count > 20 && (
          <div className="mt-8 flex justify-center">
            <p className="text-gray-400 text-sm">
              Showing {tools.results.length} of {tools.count} tools
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}