import { useState, useEffect } from 'react';
import type { Route } from './+types/tools';
import { Layout } from '../components/layout/Layout';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { LoadingState, EmptyState } from '../components/ui/Loading';
import { useInternalTools } from '../hooks/useAPI';
import { formatRelativeTime } from '../lib/utils';
import { type MCPServer, type MCPServerCreate } from '../lib/mcpApi';
import api from '../lib/api';
import { useToast } from '../hooks/useToast';
import { ToastContainer } from '../components/ui/Toast';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Tools - Agent Builder" },
    { name: "description", content: "Browse and manage available tools for your AI agents" },
  ];
}

export default function Tools() {
  const { data: tools, loading: loadingTools } = useInternalTools();
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [loadingMcp, setLoadingMcp] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingServer, setEditingServer] = useState<MCPServer | null>(null);
  const [selectedServer, setSelectedServer] = useState<MCPServer | null>(null);
  const [showToolsModal, setShowToolsModal] = useState(false);
  const [mcpTools, setMcpTools] = useState<any[]>([]);
  const { toasts, showToast, removeToast } = useToast();

  const loading = loadingTools || loadingMcp;

  useEffect(() => {
    loadMcpServers();
  }, []);

  const loadMcpServers = async () => {
    try {
      setLoadingMcp(true);
      const data = await api.getMCPServers();
      setMcpServers(Array.isArray(data) ? data : (data.results || []));
    } catch (error) {
      console.error('Failed to load MCP servers:', error);
    } finally {
      setLoadingMcp(false);
    }
  };

  const handleSync = async (id: number) => {
    try {
      showToast('Syncing tools...', 'info');
      const result = await api.syncMCPSchema(id);

      if (result.server_healthy) {
        showToast(`Discovered ${result.tools_discovered} tools!`, 'success');
        loadMcpServers();
      } else {
        showToast(`Sync failed: ${result.error}`, 'error');
      }
    } catch (error: any) {
      showToast(error.response?.data?.error || 'Failed to sync schema', 'error');
    }
  };

  const handleViewTools = async (server: MCPServer) => {
    try {
      const serverTools = await api.getMCPServerTools(server.id);
      setMcpTools(serverTools);
      setSelectedServer(server);
      setShowToolsModal(true);
    } catch (error) {
      showToast('Failed to load tools', 'error');
    }
  };

  const handleEditMcp = (server: MCPServer) => {
    setEditingServer(server);
    setShowAddModal(true);
  };

  const handleDeleteMcp = async (id: number) => {
    if (!confirm('Are you sure you want to delete this MCP server?')) return;

    try {
      await api.deleteMCPServer(id);
      showToast('MCP server deleted', 'success');
      loadMcpServers();
    } catch (error) {
      showToast('Failed to delete server', 'error');
    }
  };

  const getToolIcon = (toolType: string) => {
    const iconMap: Record<string, string> = {
      search: 'search',
      code: 'code',
      database: 'storage',
      api: 'api',
      llm: 'auto_awesome',
      mcp: 'cloud',
      default: 'extension',
    };
    return iconMap[toolType] || iconMap.default;
  };

  // Combine and filter tools
  const allTools = [
    ...(tools?.results || []).map(t => ({ ...t, category: 'internal' })),
    ...mcpServers.map(s => ({ ...s, category: 'mcp', tool_type: 'mcp' }))
  ];

  const filteredTools = allTools.filter(tool => {
    const matchesSearch = tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         tool.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterType === 'all' ||
                         (filterType === 'internal' && tool.category === 'internal') ||
                         (filterType === 'mcp' && tool.category === 'mcp') ||
                         (tool.tool_type === filterType);
    return matchesSearch && matchesFilter;
  });

  return (
    <Layout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
                Tool Library
              </h1>
              <p className="text-gray-400 mt-1">
                Browse and manage tools for your AI agents
              </p>
            </div>
            <Button onClick={() => setShowAddModal(true)}>
              <span className="material-symbols-outlined text-base mr-2">add</span>
              Register MCP Server
            </Button>
          </div>

          {/* Search and Filter */}
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                search
              </span>
              <Input
                type="text"
                placeholder="Search tools..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#1a2633] border border-[#374151] rounded-md pl-10 pr-4 py-2 focus:ring-[#1173d4] focus:border-[#1173d4] text-sm text-white"
              />
            </div>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-[#1a2633] border border-[#374151] rounded-md px-4 py-2 text-white focus:ring-[#1173d4] focus:border-[#1173d4] text-sm"
            >
              <option value="all">All Types</option>
              <option value="internal">Internal</option>
              <option value="mcp">MCP Servers</option>
              <option value="database">Database</option>
              <option value="api">API</option>
              <option value="code">Code</option>
              <option value="search">Search</option>
            </select>
          </div>
        </div>

        {/* Tools Grid */}
        {loading ? (
          <LoadingState>Loading tools...</LoadingState>
        ) : filteredTools.length === 0 ? (
          <EmptyState
            title={searchQuery || filterType !== 'all' ? "No tools found" : "No tools available"}
            description={searchQuery || filterType !== 'all' ? "Try adjusting your search or filters" : "Tools will appear here when they are added to the system"}
            icon={
              <span className="material-symbols-outlined text-4xl">extension</span>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredTools.map((tool) => (
              tool.category === 'mcp' ? (
                <MCPServerCard
                  key={`mcp-${tool.id}`}
                  server={tool as any}
                  onSync={handleSync}
                  onEdit={handleEditMcp}
                  onViewTools={handleViewTools}
                  onDelete={handleDeleteMcp}
                />
              ) : (
                <InternalToolCard key={`tool-${tool.id}`} tool={tool as any} getToolIcon={getToolIcon} />
              )
            ))}
          </div>
        )}
      </div>

      {/* Add MCP Server Modal */}
      {showAddModal && (
        <AddMCPServerModal
          server={editingServer}
          onClose={() => {
            setShowAddModal(false);
            setEditingServer(null);
          }}
          onSuccess={() => {
            setShowAddModal(false);
            setEditingServer(null);
            loadMcpServers();
            showToast(editingServer ? 'MCP server updated successfully' : 'MCP server registered successfully', 'success');
          }}
          showToast={showToast}
        />
      )}

      {/* MCP Tools Modal */}
      {showToolsModal && selectedServer && (
        <MCPToolsModal
          server={selectedServer}
          tools={mcpTools}
          onClose={() => {
            setShowToolsModal(false);
            setSelectedServer(null);
            setMcpTools([]);
          }}
        />
      )}

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </Layout>
  );
}

// Internal Tool Card Component
function InternalToolCard({ tool, getToolIcon }: { tool: any; getToolIcon: (type: string) => string }) {
  return (
    <Card className="hover:bg-[#1f2937] transition-colors">
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
            <h3 className="text-lg font-semibold text-white">{tool.name}</h3>
            <p className="text-gray-400 text-sm mt-1 line-clamp-2">
              {tool.description || 'No description provided'}
            </p>
            <div className="mt-3 flex gap-2">
              <Badge variant="secondary">Internal</Badge>
              <Badge variant="secondary">{tool.tool_type}</Badge>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-[#233648] flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Added {formatRelativeTime(tool.created_at)}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

// MCP Server Card Component
function MCPServerCard({
  server,
  onSync,
  onEdit,
  onViewTools,
  onDelete
}: {
  server: MCPServer;
  onSync: (id: number) => void;
  onEdit: (server: MCPServer) => void;
  onViewTools: (server: MCPServer) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <Card className="hover:bg-[#1f2937] transition-colors">
      <CardContent className="pt-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <div className="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center">
              <span className="material-symbols-outlined text-2xl text-purple-400">cloud</span>
            </div>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-semibold text-white">{server.name}</h3>
              <span className={`text-xs px-2 py-0.5 rounded ${
                server.is_healthy ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
              }`}>
                {server.is_healthy ? '●' : '●'}
              </span>
            </div>
            <p className="text-gray-400 text-sm mt-1 line-clamp-2">{server.description}</p>
            <div className="mt-3 flex gap-2">
              <Badge variant="secondary">MCP Server</Badge>
              <Badge variant="secondary">{server.tools_count} tools</Badge>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-[#233648] flex items-center justify-between">
          <span className="text-xs text-gray-500">{server.transport}</span>
          <div className="flex gap-2">
            <button
              onClick={() => onSync(server.id)}
              className="text-blue-400 hover:text-blue-300"
              title="Sync tools"
            >
              <span className="material-symbols-outlined text-base">sync</span>
            </button>
            <button
              onClick={() => onEdit(server)}
              className="text-blue-400 hover:text-blue-300"
              title="Edit"
            >
              <span className="material-symbols-outlined text-base">edit</span>
            </button>
            <button
              onClick={() => onViewTools(server)}
              className="text-gray-400 hover:text-white"
              title="View tools"
            >
              <span className="material-symbols-outlined text-base">visibility</span>
            </button>
            <button
              onClick={() => onDelete(server.id)}
              className="text-red-400 hover:text-red-300"
              title="Delete"
            >
              <span className="material-symbols-outlined text-base">delete</span>
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Add MCP Server Modal
function AddMCPServerModal({
  server,
  onClose,
  onSuccess,
  showToast
}: {
  server?: MCPServer | null;
  onClose: () => void;
  onSuccess: () => void;
  showToast: (message: string, type: 'success' | 'error' | 'info') => void;
}) {
  const isEditMode = !!server;
  const [formData, setFormData] = useState<MCPServerCreate>({
    name: server?.name || '',
    description: server?.description || '',
    url: server?.url || '',
    transport: server?.transport || 'sse',
    tool_prefix: server?.tool_prefix || ''
  });
  const [testing, setTesting] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ healthy: boolean; message: string } | null>(null);
  const [discoveredTools, setDiscoveredTools] = useState<any[]>([]);
  const [showTools, setShowTools] = useState(false);

  const handleTest = async () => {
    if (!formData.url) {
      showToast('Please enter a URL first', 'error');
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      const result = await api.testMCPConnection(formData.url);

      if (result.healthy) {
        setTestResult({
          healthy: true,
          message: `✓ Connected! Found ${result.tools_count || 0} tools`
        });
      } else {
        setTestResult({
          healthy: false,
          message: `✗ Connection failed: ${result.error}`
        });
      }
    } catch (error: any) {
      setTestResult({
        healthy: false,
        message: `✗ Connection failed: ${error.response?.data?.error || error.message}`
      });
    } finally {
      setTesting(false);
    }
  };

  const handleDiscover = async () => {
    if (!formData.url) {
      showToast('Please enter a URL first', 'error');
      return;
    }

    setDiscovering(true);
    setDiscoveredTools([]);

    try {
      const result = await api.discoverMCPTools(formData.url, formData.tool_prefix);

      if (result.healthy) {
        setDiscoveredTools(result.tools);
        setShowTools(true);
        showToast(`Discovered ${result.tools.length} tools`, 'success');
      } else {
        showToast(`Failed to discover tools: ${result.error}`, 'error');
      }
    } catch (error: any) {
      showToast(
        error.response?.data?.error || error.message || 'Failed to discover tools',
        'error'
      );
    } finally {
      setDiscovering(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name || !formData.url) {
      showToast('Please fill in required fields', 'error');
      return;
    }

    setSaving(true);

    try {
      if (isEditMode && server) {
        await api.updateMCPServer(server.id, formData);
      } else {
        await api.createMCPServer(formData);
      }
      onSuccess();
    } catch (error: any) {
      showToast(error.response?.data?.error || `Failed to ${isEditMode ? 'update' : 'create'} server`, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1a2633] rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">{isEditMode ? 'Edit MCP Server' : 'Register MCP Server'}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Name <span className="text-red-400">*</span>
            </label>
            <Input
              type="text"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Crawl4AI Production"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
            <Input
              type="text"
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              placeholder="e.g., Web crawling and screenshot tools"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              MCP Endpoint URL <span className="text-red-400">*</span>
            </label>
            <div className="flex gap-2">
              <Input
                type="url"
                value={formData.url}
                onChange={e => setFormData({ ...formData, url: e.target.value })}
                placeholder="http://localhost:3001/mcp"
                className="flex-1"
                required
              />
              <Button type="button" variant="outline" onClick={handleTest} disabled={testing || !formData.url}>
                {testing ? 'Testing...' : 'Test'}
              </Button>
              <Button type="button" variant="outline" onClick={handleDiscover} disabled={discovering || !formData.url}>
                {discovering ? 'Discovering...' : 'Discover'}
              </Button>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Enter the base MCP endpoint. System will append /sse and /schema as needed.
            </p>
            {testResult && (
              <p className={`text-sm mt-2 ${testResult.healthy ? 'text-green-400' : 'text-red-400'}`}>
                {testResult.message}
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Transport</label>
            <select
              value={formData.transport}
              onChange={e => setFormData({ ...formData, transport: e.target.value as 'sse' | 'stdio' | 'http' })}
              className="w-full bg-[#111a22] border border-[#374151] rounded-md px-3 py-2 text-white focus:ring-[#1173d4] focus:border-[#1173d4]"
            >
              <option value="sse">Server-Sent Events (SSE)</option>
              <option value="stdio">Standard I/O</option>
              <option value="http">Streamable HTTP</option>
            </select>
            <p className="text-xs text-gray-400 mt-1">Most MCP servers use SSE transport</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Tool Prefix (optional)</label>
            <Input
              type="text"
              value={formData.tool_prefix}
              onChange={e => setFormData({ ...formData, tool_prefix: e.target.value })}
              placeholder="e.g., c4ai"
            />
            <p className="text-xs text-gray-400 mt-1">
              Prefix for tool names to avoid conflicts (e.g., "c4ai_screenshot")
            </p>
          </div>

          {/* Discovered Tools Section */}
          {discoveredTools.length > 0 && (
            <div className="border border-[#374151] rounded-lg p-4 bg-[#111a22]">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-sm font-semibold text-white">
                  Discovered Tools ({discoveredTools.length})
                </h3>
                <button
                  type="button"
                  onClick={() => setShowTools(!showTools)}
                  className="text-[#1173d4] text-sm hover:underline"
                >
                  {showTools ? 'Hide' : 'Show'}
                </button>
              </div>

              {showTools && (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {discoveredTools.map((tool, idx) => (
                    <div key={idx} className="bg-[#1a2633] p-3 rounded border border-[#374151]">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-white">{tool.prefixed_name}</p>
                          {tool.description && (
                            <p className="text-xs text-gray-400 mt-1">{tool.description}</p>
                          )}
                          {tool.required_inputs && tool.required_inputs.length > 0 && (
                            <div className="mt-2">
                              <span className="text-xs text-gray-500">Required inputs: </span>
                              <span className="text-xs text-gray-300">
                                {tool.required_inputs.join(', ')}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                      {tool.capabilities_tags && tool.capabilities_tags.length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {tool.capabilities_tags.map((cap: string) => (
                            <span
                              key={cap}
                              className="px-2 py-0.5 bg-[#1173d4]/20 text-[#1173d4] text-xs rounded"
                            >
                              {cap}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t border-[#374151]">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>
              {saving ? (isEditMode ? 'Updating...' : 'Registering...') : (isEditMode ? 'Update Server' : 'Register Server')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// MCP Tools Modal
function MCPToolsModal({
  server,
  tools,
  onClose
}: {
  server: MCPServer;
  tools: any[];
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1a2633] rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-bold text-white">{server.name} - Available Tools</h2>
            <p className="text-sm text-gray-400 mt-1">{tools.length} tools discovered</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {tools.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            No tools found. Try syncing the server schema.
          </div>
        ) : (
          <div className="space-y-3">
            {tools.map(tool => (
              <div key={tool.id} className="bg-[#111a22] p-4 rounded-lg border border-[#374151]">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <code className="text-[#1173d4] font-mono text-sm">{tool.prefixed_name}</code>
                    {tool.title && (
                      <span className="text-gray-400 text-sm ml-2">({tool.title})</span>
                    )}
                  </div>
                  {tool.capabilities_tags.length > 0 && (
                    <div className="flex gap-1">
                      {tool.capabilities_tags.map((tag: string) => (
                        <span key={tag} className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {tool.description && (
                  <p className="text-sm text-gray-300 mb-2">{tool.description}</p>
                )}

                {tool.required_inputs.length > 0 && (
                  <div className="text-xs">
                    <span className="text-gray-500">Required inputs:</span>
                    <code className="ml-2 text-gray-300">{tool.required_inputs.join(', ')}</code>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-end mt-6 pt-4 border-t border-[#374151]">
          <Button onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  );
}
