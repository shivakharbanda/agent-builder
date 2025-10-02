import axios, { type AxiosInstance } from 'axios';
import { WORKFLOW_BUILDER_CONFIG, APP_CONFIG } from './config';
import { api } from './api';

export interface WorkflowBuilderMessage {
  role: 'user' | 'model';
  timestamp: string;
  content: string;
}

export interface WorkflowBuilderSession {
  session_id: string;
}

export interface GenerateRequest {
  prompt: string;
  session_id: string;
}

export interface WorkflowConfig {
  name: string;
  description: string;
  nodes: Array<{
    id: string;
    type: string;
    position: { x: number; y: number };
    config: Record<string, any>;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
  }>;
  properties?: {
    timeout?: number;
    retry_count?: number;
    schedule?: string;
    watermark_start_date?: string;
    watermark_end_date?: string;
    notification_email?: string;
  };
}

class WorkflowBuilderAPIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: WORKFLOW_BUILDER_CONFIG.BASE_URL,
      timeout: WORKFLOW_BUILDER_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for debugging
    this.client.interceptors.request.use(
      (config) => {
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.log('Workflow Builder API Request:', config);
        }
        return config;
      },
      (error) => {
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.error('Workflow Builder API Request Error:', error);
        }
        return Promise.reject(error);
      }
    );

    // Response interceptor for debugging
    this.client.interceptors.response.use(
      (response) => {
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.log('Workflow Builder API Response:', response);
        }
        return response;
      },
      (error) => {
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.error('Workflow Builder API Response Error:', error);
        }
        return Promise.reject(error);
      }
    );
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.client.get(WORKFLOW_BUILDER_CONFIG.HEALTH_ENDPOINT);
      return response.status === 200;
    } catch {
      return false;
    }
  }

  async registerSessionWithDjango(projectId: number): Promise<{session_id: string}> {
    /**
     * Step 1: Register session with Django backend
     * This creates WorkflowBuilderSession record with user/project mapping
     */
    const response = await (api as any).client.post<{session_id: string}>(
      '/builder-tools/register_session/',
      { project_id: projectId }
    );
    return response.data;
  }

  async initializeFastAPISession(sessionId: string): Promise<WorkflowBuilderSession> {
    /**
     * Step 2: Initialize FastAPI session with session_id from Django
     * FastAPI is stateless - just sets up usage tracking
     */
    const response = await this.client.post<WorkflowBuilderSession>(
      WORKFLOW_BUILDER_CONFIG.SESSION_ENDPOINT,
      { session_id: sessionId }
    );
    return response.data;
  }

  async createSession(projectId: number): Promise<WorkflowBuilderSession> {
    /**
     * Complete two-step session creation:
     * 1. Register with Django (gets session_id, maps to user/project)
     * 2. Initialize with FastAPI (sets up chat)
     */
    const { session_id } = await this.registerSessionWithDjango(projectId);
    const session = await this.initializeFastAPISession(session_id);
    return session;
  }

  async resetSession(sessionId: string): Promise<void> {
    await this.client.post(WORKFLOW_BUILDER_CONFIG.RESET_ENDPOINT, {
      session_id: sessionId,
    });
  }

  async *generateStream(
    prompt: string,
    sessionId: string
  ): AsyncGenerator<WorkflowBuilderMessage, void, unknown> {
    const response = await fetch(
      `${WORKFLOW_BUILDER_CONFIG.BASE_URL}${WORKFLOW_BUILDER_CONFIG.GENERATE_ENDPOINT}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/plain',
        },
        body: JSON.stringify({ prompt, session_id: sessionId }),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim()) {
            try {
              const message = JSON.parse(line) as WorkflowBuilderMessage;
              yield message;
            } catch (e) {
              console.warn('Failed to parse message:', line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async finalizeWorkflowConfig(sessionId: string): Promise<WorkflowConfig | null> {
    try {
      const response = await this.client.get(
        `${WORKFLOW_BUILDER_CONFIG.GENERATE_FINALIZE_ENDPOINT}?session_id=${sessionId}`
      );

      if (response.status === 202) {
        return null; // Not finalized yet
      }

      return response.data as WorkflowConfig;
    } catch (error: any) {
      if (error.response?.status === 202) {
        return null; // Not finalized yet
      }
      throw error;
    }
  }

  async getChatHistory(sessionId: string): Promise<WorkflowBuilderMessage[]> {
    const response = await this.client.get(
      `/chat/?session_id=${sessionId}`
    );

    const lines = response.data.split('\n').filter((line: string) => line.trim());
    return lines.map((line: string) => JSON.parse(line) as WorkflowBuilderMessage);
  }
}

export const workflowBuilderApi = new WorkflowBuilderAPIClient();
export default workflowBuilderApi;
