import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import { API_CONFIG, APP_CONFIG } from './config';
import type {
  Project, ProjectCreate,
  Agent, AgentCreate, AgentCompleteCreate,
  Prompt, PromptCreate,
  Tool, ToolCreate,
  AgentTool, AgentToolCreate,
  Workflow, WorkflowCreate, WorkflowProperties,
  DataSource, DataSourceCreate,
  WorkflowNode, WorkflowNodeCreate,
  PlaceholderMapping, PlaceholderMappingCreate,
  OutputNode, OutputNodeCreate,
  CredentialCategory, CredentialType, CredentialField,
  Credential, CredentialCreate, CredentialUpdate,
  PaginatedResponse,
  APIError,
  LoginRequest,
  LoginResponse,
  User,
  AuthCheckResponse
} from './types';

// Network connectivity state
let isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;
let lastConnectivityCheck = 0;

class AgentBuilderAPI {
  private client: AxiosInstance;
  private retryAttempts: number = API_CONFIG.RETRY_ATTEMPTS;

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
      // Enable credentials for cookie-based auth
      withCredentials: true,
    });

    // Set up connectivity monitoring
    this.setupConnectivityMonitoring();

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {

        // Add CSRF token if available
        const csrfToken = this.getCSRFToken();
        if (csrfToken) {
          config.headers['X-CSRFToken'] = csrfToken;
        }

        // Add timestamp to prevent caching
        if (config.method === 'get') {
          config.params = { ...config.params, _t: Date.now() };
        }

        return config;
      },
      (error) => {
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.error('API Request Error:', error);
        }
        return Promise.reject(error);
      }
    );

    // Response interceptor with retry logic
    this.client.interceptors.response.use(
      (response) => {
        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as any;

        if (APP_CONFIG.ENABLE_DEBUG) {
          console.error('API Response Error:', error);
        }

        // Handle network errors with retry
        if (error.code === 'NETWORK_ERROR' || error.code === 'ECONNABORTED') {
          if (!originalRequest._retry && originalRequest._retryCount < this.retryAttempts) {
            originalRequest._retry = true;
            originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;

            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, API_CONFIG.RETRY_DELAY * originalRequest._retryCount));

            return this.client(originalRequest);
          }
        }

        // Transform error to our APIError format
        const apiError: APIError = {
          detail: this.getErrorMessage(error),
          status: error.response?.status,
          code: error.code,
          ...(error.response?.data && typeof error.response.data === 'object' ? error.response.data : {}),
        };

        return Promise.reject(apiError);
      }
    );
  }

  private setupConnectivityMonitoring() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        isOnline = true;
      });

      window.addEventListener('offline', () => {
        isOnline = false;
      });
    }
  }

  private getErrorMessage(error: AxiosError): string {
    if (!isOnline) {
      return 'No internet connection. Please check your network and try again.';
    }

    if (error.code === 'ECONNABORTED') {
      return 'Request timed out. Please try again.';
    }

    if (error.code === 'NETWORK_ERROR') {
      return 'Unable to connect to server. Please check if the backend is running.';
    }

    if (error.response?.status === 404) {
      return 'The requested resource was not found.';
    }

    if (error.response?.status === 500) {
      return 'Server error. Please try again later.';
    }

    if (error.response?.status === 403) {
      return 'You do not have permission to access this resource.';
    }

    if (error.response?.status === 401) {
      return 'You need to log in to access this resource.';
    }

    return error.response?.data?.detail || error.message || 'An unexpected error occurred.';
  }

  // Network connectivity check
  async checkConnectivity(): Promise<boolean> {
    const now = Date.now();
    if (now - lastConnectivityCheck < 5000) {
      return isOnline;
    }

    try {
      await this.client.get('/health/', { timeout: 5000 });
      isOnline = true;
      lastConnectivityCheck = now;
      return true;
    } catch {
      isOnline = false;
      lastConnectivityCheck = now;
      return false;
    }
  }

  // Get current connectivity status
  isConnected(): boolean {
    return isOnline;
  }

  private getCSRFToken(): string | null {
    if (typeof document !== 'undefined') {
      const name = 'csrftoken';
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        const [key, value] = cookie.trim().split('=');
        if (key === name) {
          return decodeURIComponent(value);
        }
      }
    }
    return null;
  }

  // Projects API
  async getProjects(): Promise<PaginatedResponse<Project>> {
    const response = await this.client.get<PaginatedResponse<Project>>('/projects/');
    return response.data;
  }

  async getProject(id: number): Promise<Project> {
    const response = await this.client.get<Project>(`/projects/${id}/`);
    return response.data;
  }

  async createProject(data: ProjectCreate): Promise<Project> {
    const response = await this.client.post<Project>('/projects/', data);
    return response.data;
  }

  async updateProject(id: number, data: Partial<ProjectCreate>): Promise<Project> {
    const response = await this.client.put<Project>(`/projects/${id}/`, data);
    return response.data;
  }

  async deleteProject(id: number): Promise<void> {
    await this.client.delete(`/projects/${id}/`);
  }

  async getProjectAgents(id: number): Promise<Agent[]> {
    const response = await this.client.get<Agent[]>(`/projects/${id}/agents/`);
    return response.data;
  }

  async getProjectWorkflows(id: number): Promise<Workflow[]> {
    const response = await this.client.get<Workflow[]>(`/projects/${id}/workflows/`);
    return response.data;
  }

  // Agents API
  async getAgents(projectId?: number): Promise<PaginatedResponse<Agent>> {
    const params = projectId ? { project: projectId } : {};
    const response = await this.client.get<PaginatedResponse<Agent>>('/agents/', { params });
    return response.data;
  }

  async getAgent(id: number): Promise<Agent> {
    const response = await this.client.get<Agent>(`/agents/${id}/`);
    return response.data;
  }

  async createAgent(data: AgentCreate): Promise<Agent> {
    const response = await this.client.post<Agent>('/agents/', data);
    return response.data;
  }

  async createAgentComplete(data: AgentCompleteCreate): Promise<Agent> {
    const response = await this.client.post<Agent>('/agents/create-complete/', data);
    return response.data;
  }

  async updateAgent(id: number, data: Partial<AgentCreate>): Promise<Agent> {
    const response = await this.client.put<Agent>(`/agents/${id}/`, data);
    return response.data;
  }

  async deleteAgent(id: number): Promise<void> {
    await this.client.delete(`/agents/${id}/`);
  }

  async getAgentPrompts(id: number): Promise<Prompt[]> {
    const response = await this.client.get<Prompt[]>(`/agents/${id}/prompts/`);
    return response.data;
  }

  async getAgentTools(id: number): Promise<AgentTool[]> {
    const response = await this.client.get<AgentTool[]>(`/agents/${id}/tools/`);
    return response.data;
  }

  // Prompts API
  async getPrompts(agentId?: number): Promise<PaginatedResponse<Prompt>> {
    const params = agentId ? { agent: agentId } : {};
    const response = await this.client.get<PaginatedResponse<Prompt>>('/prompts/', { params });
    return response.data;
  }

  async getPrompt(id: number): Promise<Prompt> {
    const response = await this.client.get<Prompt>(`/prompts/${id}/`);
    return response.data;
  }

  async createPrompt(data: PromptCreate): Promise<Prompt> {
    const response = await this.client.post<Prompt>('/prompts/', data);
    return response.data;
  }

  async updatePrompt(id: number, data: Partial<PromptCreate>): Promise<Prompt> {
    const response = await this.client.put<Prompt>(`/prompts/${id}/`, data);
    return response.data;
  }

  async deletePrompt(id: number): Promise<void> {
    await this.client.delete(`/prompts/${id}/`);
  }

  // Tools API
  async getTools(): Promise<PaginatedResponse<Tool>> {
    const response = await this.client.get<PaginatedResponse<Tool>>('/tools/');
    return response.data;
  }

  async getTool(id: number): Promise<Tool> {
    const response = await this.client.get<Tool>(`/tools/${id}/`);
    return response.data;
  }

  async createTool(data: ToolCreate): Promise<Tool> {
    const response = await this.client.post<Tool>('/tools/', data);
    return response.data;
  }

  async updateTool(id: number, data: Partial<ToolCreate>): Promise<Tool> {
    const response = await this.client.put<Tool>(`/tools/${id}/`, data);
    return response.data;
  }

  async deleteTool(id: number): Promise<void> {
    await this.client.delete(`/tools/${id}/`);
  }

  // Agent-Tool relationships

  async createAgentTool(data: AgentToolCreate): Promise<AgentTool> {
    const response = await this.client.post<AgentTool>('/agent-tools/', data);
    return response.data;
  }

  async updateAgentTool(id: number, data: Partial<AgentToolCreate>): Promise<AgentTool> {
    const response = await this.client.put<AgentTool>(`/agent-tools/${id}/`, data);
    return response.data;
  }

  async deleteAgentTool(id: number): Promise<void> {
    await this.client.delete(`/agent-tools/${id}/`);
  }

  // Workflows API
  async getWorkflows(projectId?: number): Promise<PaginatedResponse<Workflow>> {
    const params = projectId ? { project: projectId } : {};
    const response = await this.client.get<PaginatedResponse<Workflow>>('/workflows/', { params });
    return response.data;
  }

  async getWorkflow(id: number): Promise<Workflow> {
    const response = await this.client.get<Workflow>(`/workflows/${id}/`);
    return response.data;
  }

  async createWorkflow(data: WorkflowCreate): Promise<Workflow> {
    const response = await this.client.post<Workflow>('/workflows/', data);
    return response.data;
  }

  async saveCompleteWorkflow(data: {
    name: string;
    description: string;
    project: number;
    configuration: any;
    properties: any;
  }): Promise<Workflow> {
    const response = await this.client.post<Workflow>('/workflows/save_complete/', data);
    return response.data;
  }

  async updateCompleteWorkflow(id: number, data: {
    name: string;
    description: string;
    configuration: any;
    properties: any;
  }): Promise<Workflow> {
    const response = await this.client.put<Workflow>(`/workflows/${id}/update_complete/`, data);
    return response.data;
  }

  async updateWorkflow(id: number, data: Partial<WorkflowCreate>): Promise<Workflow> {
    const response = await this.client.put<Workflow>(`/workflows/${id}/`, data);
    return response.data;
  }

  async deleteWorkflow(id: number): Promise<void> {
    await this.client.delete(`/workflows/${id}/`);
  }

  async getWorkflowNodes(id: number): Promise<WorkflowNode[]> {
    const response = await this.client.get<WorkflowNode[]>(`/workflows/${id}/nodes/`);
    return response.data;
  }

  async getWorkflowProperties(id: number): Promise<WorkflowProperties> {
    const response = await this.client.get<WorkflowProperties>(`/workflows/${id}/properties/`);
    return response.data;
  }

  async updateWorkflowProperties(id: number, data: Partial<WorkflowProperties>): Promise<WorkflowProperties> {
    const response = await this.client.put<WorkflowProperties>(`/workflows/${id}/properties/`, data);
    return response.data;
  }

  // Data Sources API
  async getDataSources(): Promise<PaginatedResponse<DataSource>> {
    const response = await this.client.get<PaginatedResponse<DataSource>>('/data-sources/');
    return response.data;
  }

  async getDataSource(id: number): Promise<DataSource> {
    const response = await this.client.get<DataSource>(`/data-sources/${id}/`);
    return response.data;
  }

  async createDataSource(data: DataSourceCreate): Promise<DataSource> {
    const response = await this.client.post<DataSource>('/data-sources/', data);
    return response.data;
  }

  async updateDataSource(id: number, data: Partial<DataSourceCreate>): Promise<DataSource> {
    const response = await this.client.put<DataSource>(`/data-sources/${id}/`, data);
    return response.data;
  }

  async deleteDataSource(id: number): Promise<void> {
    await this.client.delete(`/data-sources/${id}/`);
  }

  // Workflow Nodes API

  async getWorkflowNode(id: number): Promise<WorkflowNode> {
    const response = await this.client.get<WorkflowNode>(`/workflow-nodes/${id}/`);
    return response.data;
  }

  async createWorkflowNode(data: WorkflowNodeCreate): Promise<WorkflowNode> {
    const response = await this.client.post<WorkflowNode>('/workflow-nodes/', data);
    return response.data;
  }

  async updateWorkflowNode(id: number, data: Partial<WorkflowNodeCreate>): Promise<WorkflowNode> {
    const response = await this.client.put<WorkflowNode>(`/workflow-nodes/${id}/`, data);
    return response.data;
  }

  async deleteWorkflowNode(id: number): Promise<void> {
    await this.client.delete(`/workflow-nodes/${id}/`);
  }

  async getNodeMappings(id: number): Promise<PlaceholderMapping[]> {
    const response = await this.client.get<PlaceholderMapping[]>(`/workflow-nodes/${id}/mappings/`);
    return response.data;
  }

  // Placeholder Mappings API
  async getPlaceholderMappings(): Promise<PaginatedResponse<PlaceholderMapping>> {
    const response = await this.client.get<PaginatedResponse<PlaceholderMapping>>('/placeholder-mappings/');
    return response.data;
  }

  async createPlaceholderMapping(data: PlaceholderMappingCreate): Promise<PlaceholderMapping> {
    const response = await this.client.post<PlaceholderMapping>('/placeholder-mappings/', data);
    return response.data;
  }

  async updatePlaceholderMapping(id: number, data: Partial<PlaceholderMappingCreate>): Promise<PlaceholderMapping> {
    const response = await this.client.put<PlaceholderMapping>(`/placeholder-mappings/${id}/`, data);
    return response.data;
  }

  async deletePlaceholderMapping(id: number): Promise<void> {
    await this.client.delete(`/placeholder-mappings/${id}/`);
  }

  // Output Nodes API
  async getOutputNodes(): Promise<PaginatedResponse<OutputNode>> {
    const response = await this.client.get<PaginatedResponse<OutputNode>>('/output-nodes/');
    return response.data;
  }

  async createOutputNode(data: OutputNodeCreate): Promise<OutputNode> {
    const response = await this.client.post<OutputNode>('/output-nodes/', data);
    return response.data;
  }

  async updateOutputNode(id: number, data: Partial<OutputNodeCreate>): Promise<OutputNode> {
    const response = await this.client.put<OutputNode>(`/output-nodes/${id}/`, data);
    return response.data;
  }

  async deleteOutputNode(id: number): Promise<void> {
    await this.client.delete(`/output-nodes/${id}/`);
  }

  // Credentials API
  async getCredentialCategories(): Promise<PaginatedResponse<CredentialCategory>> {
    const response = await this.client.get<PaginatedResponse<CredentialCategory>>('/credentials/categories/');
    return response.data;
  }

  async getCredentialCategory(id: number): Promise<CredentialCategory> {
    const response = await this.client.get<CredentialCategory>(`/credentials/categories/${id}/`);
    return response.data;
  }

  async getCategoryTypes(id: number): Promise<CredentialType[]> {
    const response = await this.client.get<CredentialType[]>(`/credentials/categories/${id}/types/`);
    return response.data;
  }

  async getCredentialTypes(categoryId?: number): Promise<PaginatedResponse<CredentialType>> {
    const params = categoryId ? { category: categoryId } : {};
    const response = await this.client.get<PaginatedResponse<CredentialType>>('/credentials/types/', { params });
    return response.data;
  }

  async getCredentialType(id: number): Promise<CredentialType> {
    const response = await this.client.get<CredentialType>(`/credentials/types/${id}/`);
    return response.data;
  }

  async getCredentialTypeFields(id: number): Promise<CredentialField[]> {
    const response = await this.client.get<CredentialField[]>(`/credentials/types/${id}/fields/`);
    return response.data;
  }

  async getCredentials(): Promise<PaginatedResponse<Credential>> {
    const response = await this.client.get<PaginatedResponse<Credential>>('/credentials/credentials/');
    return response.data;
  }

  async getCredential(id: number): Promise<Credential> {
    const response = await this.client.get<Credential>(`/credentials/credentials/${id}/`);
    return response.data;
  }

  async createCredential(data: CredentialCreate): Promise<Credential> {
    const response = await this.client.post<Credential>('/credentials/credentials/', data);
    return response.data;
  }

  async updateCredential(id: number, data: CredentialUpdate): Promise<Credential> {
    const response = await this.client.put<Credential>(`/credentials/credentials/${id}/`, data);
    return response.data;
  }

  async deleteCredential(id: number): Promise<void> {
    await this.client.delete(`/credentials/credentials/${id}/`);
  }

  async restoreCredential(id: number): Promise<Credential> {
    const response = await this.client.post<Credential>(`/credentials/credentials/${id}/restore/`);
    return response.data;
  }

  async getCredentialConnectionDetails(id: number): Promise<{
    credential_id: number;
    credential_name: string;
    credential_type: string;
    details: Record<string, string>;
  }> {
    const response = await this.client.get(`/credentials/credentials/${id}/connection_details/`);
    return response.data;
  }

  // Authentication API
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.client.post<LoginResponse>('/auth/token/', credentials);
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout/');
  }

  async checkAuth(): Promise<AuthCheckResponse> {
    const response = await this.client.get<AuthCheckResponse>('/auth/check-auth/');
    return response.data;
  }

  async refreshToken(): Promise<void> {
    await this.client.post('/auth/token/refresh/');
  }
}

// Create and export a singleton instance
export const api = new AgentBuilderAPI();
export default api;