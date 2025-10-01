import axios, { type AxiosInstance } from 'axios';
import { AGENT_BUILDER_CONFIG, APP_CONFIG } from './config';

export interface AgentBuilderMessage {
  role: 'user' | 'model';
  timestamp: string;
  content: string;
}

export interface AgentBuilderSession {
  session_id: string;
}

export interface GenerateRequest {
  prompt: string;
  session_id: string;
}

export interface AgentConfig {
  name: string;
  description: string;
  return_type: 'structured' | 'unstructured';
  prompts: Array<{
    prompt_type: 'system' | 'user';
    content: string;
    placeholders: Record<string, string>;
  }>;
  schema_definition?: Record<string, any>;
}

class AgentBuilderAPIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: AGENT_BUILDER_CONFIG.BASE_URL,
      timeout: AGENT_BUILDER_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for debugging
    this.client.interceptors.request.use(
      (config) => {
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.log('Agent Builder API Request:', config);
        }
        return config;
      },
      (error) => {
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.error('Agent Builder API Request Error:', error);
        }
        return Promise.reject(error);
      }
    );

    // Response interceptor for debugging
    this.client.interceptors.response.use(
      (response) => {
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.log('Agent Builder API Response:', response);
        }
        return response;
      },
      (error) => {
        if (APP_CONFIG.ENABLE_DEBUG) {
          console.error('Agent Builder API Response Error:', error);
        }
        return Promise.reject(error);
      }
    );
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.client.get(AGENT_BUILDER_CONFIG.HEALTH_ENDPOINT);
      return response.status === 200;
    } catch {
      return false;
    }
  }

  async createSession(): Promise<AgentBuilderSession> {
    const response = await this.client.post<AgentBuilderSession>(
      AGENT_BUILDER_CONFIG.SESSION_ENDPOINT
    );
    return response.data;
  }

  async resetSession(sessionId: string): Promise<void> {
    await this.client.post(AGENT_BUILDER_CONFIG.RESET_ENDPOINT, {
      session_id: sessionId,
    });
  }

  async *generateStream(
    prompt: string,
    sessionId: string
  ): AsyncGenerator<AgentBuilderMessage, void, unknown> {
    const response = await fetch(
      `${AGENT_BUILDER_CONFIG.BASE_URL}${AGENT_BUILDER_CONFIG.GENERATE_ENDPOINT}`,
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
              const message = JSON.parse(line) as AgentBuilderMessage;
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

  async finalizeAgentConfig(sessionId: string): Promise<AgentConfig | null> {
    try {
      const response = await this.client.get(
        `${AGENT_BUILDER_CONFIG.GENERATE_FINALIZE_ENDPOINT}?session_id=${sessionId}`
      );

      if (response.status === 202) {
        return null; // Not finalized yet
      }

      return response.data as AgentConfig;
    } catch (error: any) {
      if (error.response?.status === 202) {
        return null; // Not finalized yet
      }
      throw error;
    }
  }

  async getChatHistory(sessionId: string): Promise<AgentBuilderMessage[]> {
    const response = await this.client.get(
      `${AGENT_BUILDER_CONFIG.CHAT_ENDPOINT}?session_id=${sessionId}`
    );

    const lines = response.data.split('\n').filter((line: string) => line.trim());
    return lines.map((line: string) => JSON.parse(line) as AgentBuilderMessage);
  }
}

export const agentBuilderApi = new AgentBuilderAPIClient();
export default agentBuilderApi;