import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface MCPServer {
  id: number;
  name: string;
  description: string;
  url: string;
  transport: 'sse' | 'stdio' | 'http';
  tool_prefix: string;
  is_healthy: boolean;
  last_schema_sync: string | null;
  tools_count: number;
  created_at: string;
  is_active: boolean;
}

export interface MCPServerCreate {
  name: string;
  description: string;
  url: string;
  transport: 'sse' | 'stdio' | 'http';
  tool_prefix: string;
}

export interface MCPTool {
  id: number;
  name: string;
  prefixed_name: string;
  title: string;
  description: string;
  input_schema: any;
  output_schema: any;
  capabilities_tags: string[];
  required_inputs: string[];
  created_at: string;
}

export interface ConnectionTestResult {
  healthy: boolean;
  error: string | null;
  tools_count?: number;
}

export interface SyncResult {
  tools_discovered: number;
  tools_stored: number;
  server_healthy: boolean;
  error: string | null;
}

export interface DiscoverResult {
  healthy: boolean;
  tools: MCPTool[];
  error: string | null;
}

export const mcpApi = {
  /**
   * List all MCP servers
   */
  async listServers(): Promise<MCPServer[]> {
    const response = await axios.get(`${API_URL}/mcp-servers/`);
    return response.data;
  },

  /**
   * Get single MCP server details
   */
  async getServer(id: number): Promise<MCPServer> {
    const response = await axios.get(`${API_URL}/mcp-servers/${id}/`);
    return response.data;
  },

  /**
   * Create new MCP server
   */
  async createServer(data: MCPServerCreate): Promise<MCPServer> {
    const response = await axios.post(`${API_URL}/mcp-servers/`, data);
    return response.data;
  },

  /**
   * Update MCP server
   */
  async updateServer(id: number, data: Partial<MCPServerCreate>): Promise<MCPServer> {
    const response = await axios.patch(`${API_URL}/mcp-servers/${id}/`, data);
    return response.data;
  },

  /**
   * Delete MCP server (soft delete)
   */
  async deleteServer(id: number): Promise<void> {
    await axios.delete(`${API_URL}/mcp-servers/${id}/`);
  },

  /**
   * Test connection to MCP server URL
   */
  async testConnection(url: string): Promise<ConnectionTestResult> {
    const response = await axios.post(`${API_URL}/mcp-servers/test_connection/`, { url });
    return response.data;
  },

  /**
   * Discover tools from MCP server without saving
   */
  async discoverTools(url: string, toolPrefix?: string): Promise<DiscoverResult> {
    const response = await axios.post(`${API_URL}/mcp-servers/discover_tools/`, {
      url,
      tool_prefix: toolPrefix || ''
    });
    return response.data;
  },

  /**
   * Sync schema and discover tools from MCP server
   */
  async syncSchema(id: number): Promise<SyncResult> {
    const response = await axios.post(`${API_URL}/mcp-servers/${id}/sync_schema/`);
    return response.data;
  },

  /**
   * Get all tools from a specific MCP server
   */
  async getServerTools(id: number): Promise<MCPTool[]> {
    const response = await axios.get(`${API_URL}/mcp-servers/${id}/tools/`);
    return response.data;
  },

  /**
   * Attach MCP server to an agent
   */
  async attachServerToAgent(agentId: number, serverId: number): Promise<any> {
    const response = await axios.post(`${API_URL}/agents/agent-mcp-servers/`, {
      agent: agentId,
      mcp_server: serverId
    });
    return response.data;
  },

  /**
   * Detach MCP server from agent
   */
  async detachServerFromAgent(relationshipId: number): Promise<void> {
    await axios.delete(`${API_URL}/agents/agent-mcp-servers/${relationshipId}/`);
  },

  /**
   * Get all MCP servers attached to an agent
   */
  async getAgentServers(agentId: number): Promise<any[]> {
    const response = await axios.get(`${API_URL}/agents/agent-mcp-servers/?agent=${agentId}`);
    return response.data;
  }
};
