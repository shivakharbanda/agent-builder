// Base model interface with audit fields
export interface BaseModel {
  id: number;
  created_at: string;
  updated_at: string;
  created_by?: number;
  is_active: boolean;
}

// Project types
export interface Project extends BaseModel {
  name: string;
  description: string;
  agents_count?: number;
  workflows_count?: number;
}

export interface ProjectCreate {
  name: string;
  description: string;
}

// Agent types
export type ReturnType = 'structured' | 'unstructured';

export interface Agent extends BaseModel {
  name: string;
  description: string;
  return_type: ReturnType;
  schema_definition?: Record<string, any>;
  project: number;
  project_name?: string;
  prompts?: Prompt[];
  agent_tools?: AgentTool[];
  prompts_count?: number;
  tools_count?: number;
}

export interface AgentCreate {
  name: string;
  description: string;
  return_type: ReturnType;
  schema_definition?: Record<string, any>;
  project: number;
}

export interface PromptCreateData {
  prompt_type: PromptType;
  content: string;
  placeholders: Record<string, string>;
}

export interface AgentCompleteCreate {
  name: string;
  description: string;
  return_type: ReturnType;
  schema_definition?: Record<string, any>;
  project: number;
  prompts?: PromptCreateData[];
  tool_ids?: number[];
}

// Prompt types
export type PromptType = 'system' | 'user';

export interface Prompt extends BaseModel {
  agent?: number;
  prompt_type: PromptType;
  content: string;
  placeholders: Record<string, string>;
}

export interface PromptCreate {
  agent: number;
  prompt_type: PromptType;
  content: string;
  placeholders: Record<string, string>;
}

// Tool types
export interface Tool extends BaseModel {
  name: string;
  description: string;
  tool_type: string;
  configuration: Record<string, any>;
}

export interface ToolCreate {
  name: string;
  description: string;
  tool_type: string;
  configuration: Record<string, any>;
}

export interface AgentTool extends BaseModel {
  tool: number;
  tool_name?: string;
  tool_type?: string;
  configuration: Record<string, any>;
}

export interface AgentToolCreate {
  agent: number;
  tool: number;
  configuration: Record<string, any>;
}

// Workflow types
export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'completed';
export type LoadMode = 'full' | 'incremental';
export type SourceType = 'database' | 'file' | 'api';
export type NodeType = 'input' | 'agent' | 'output';

export interface DataSource extends BaseModel {
  name: string;
  source_type: SourceType;
  connection_config: Record<string, any>;
  load_mode: LoadMode;
  watermark_start_date?: string;
  watermark_end_date?: string;
  table_name: string;
}

export interface DataSourceCreate {
  name: string;
  source_type: SourceType;
  connection_config: Record<string, any>;
  load_mode: LoadMode;
  watermark_start_date?: string;
  watermark_end_date?: string;
  table_name: string;
}

export interface WorkflowProperties extends BaseModel {
  watermark_start_date?: string;
  watermark_end_date?: string;
  schedule?: string;
  timeout?: number;
  retry_count?: number;
  notification_email?: string;
}

export interface WorkflowExecution extends BaseModel {
  status: WorkflowStatus;
  started_at?: string;
  completed_at?: string;
  execution_log?: Record<string, any>;
  error_message?: string;
  triggered_by?: 'manual' | 'schedule' | 'api' | 'webhook';
}

export interface Workflow extends BaseModel {
  name: string;
  description: string;
  project: number;
  project_name?: string;
  configuration: Record<string, any>;
  status?: WorkflowStatus;
  properties?: WorkflowProperties;
  current_execution?: {
    id: number;
    status: WorkflowStatus;
    created_at: string;
  };
  nodes?: WorkflowNode[];
  output_nodes?: OutputNode[];
  nodes_count?: number;
}

export interface WorkflowCreate {
  name: string;
  description: string;
  project: number;
  configuration?: Record<string, any>;
}

export interface WorkflowNode extends BaseModel {
  workflow?: number;
  node_type: NodeType;
  position: number;
  visual_position?: { x: number; y: number };
  configuration: Record<string, any>;
  agent?: number;
  agent_name?: string;
  data_source?: number;
  data_source_name?: string;
  placeholder_mappings?: PlaceholderMapping[];
}

export interface WorkflowNodeCreate {
  workflow: number;
  node_type: NodeType;
  position: number;
  configuration: Record<string, any>;
  agent?: number;
  data_source?: number;
}

export interface PlaceholderMapping extends BaseModel {
  workflow_node?: number;
  placeholder_name: string;
  data_column: string;
  transformation: string;
}

export interface PlaceholderMappingCreate {
  workflow_node: number;
  placeholder_name: string;
  data_column: string;
  transformation: string;
}

export interface OutputNode extends BaseModel {
  workflow?: number;
  destination_table: string;
  configuration: Record<string, any>;
}

export interface OutputNodeCreate {
  workflow: number;
  destination_table: string;
  configuration: Record<string, any>;
}

// API Response types
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface APIError {
  detail?: string;
  status?: number;
  code?: string;
  [key: string]: any;
}

// Authentication types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  detail: string;
  access: string;
  refresh: string;
  user_id: number;
  username: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface AuthCheckResponse {
  authenticated: boolean;
  user: User;
}

// Form types
export interface FormState {
  loading: boolean;
  error: string | null;
  success: boolean;
}

// UI Component types
export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface TabItem {
  id: string;
  label: string;
  content: React.ReactNode;
}

// Theme types
export interface Theme {
  colors: {
    primary: string;
    background: string;
    surface: string;
    card: string;
    text: string;
    textSecondary: string;
    success: string;
    error: string;
    warning: string;
  };
}

export const defaultTheme: Theme = {
  colors: {
    primary: '#1173d4',
    background: '#111a22',
    surface: '#233648',
    card: '#1a2633',
    text: '#ffffff',
    textSecondary: '#9ca3af',
    success: '#10b981',
    error: '#ef4444',
    warning: '#f59e0b',
  },
};

// Credential types
export type FieldType = 'text' | 'password' | 'url' | 'email' | 'number' | 'textarea' | 'select' | 'checkbox';

export interface CredentialCategory extends BaseModel {
  name: string;
  description: string;
  icon: string;
  types_count?: number;
}

export interface CredentialField extends BaseModel {
  field_name: string;
  field_type: FieldType;
  is_required: boolean;
  is_secure: boolean;
  order: number;
  placeholder: string;
  help_text: string;
}

export interface CredentialType extends BaseModel {
  category: number;
  category_name?: string;
  category_icon?: string;
  type_name: string;
  type_description: string;
  handler_class_name?: string;
  fields?: CredentialField[];
  fields_count?: number;
}

export interface CredentialDetail extends BaseModel {
  field: number;
  field_name?: string;
  field_type?: FieldType;
  is_secure?: boolean;
  value: string;
}

export interface Credential extends BaseModel {
  name: string;
  description: string;
  credential_type: number;
  credential_type_name?: string;
  details?: CredentialDetail[];
  details_count?: number;
  is_deleted: boolean;
}

export interface CredentialCreate {
  name: string;
  description: string;
  credential_type: number;
  credential_details: Record<string, string>;
}

export interface CredentialUpdate {
  name: string;
  description: string;
  credential_details?: Record<string, string>;
}