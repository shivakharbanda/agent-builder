import { useState, useCallback } from 'react';
import axios from 'axios';
import type { AxiosInstance } from 'axios';
import { WORKFLOW_BUILDER_CONFIG } from '../lib/config';

interface Message {
  role: 'user' | 'model';
  content: string;
  timestamp: string;
}

interface WorkflowBuilderSession {
  sessionId: string | null;
  messages: Message[];
  isLoading: boolean;
  isConnected: boolean;
  finalConfig: any | null;
  isComplete: boolean;
}

// Create axios instance for FastAPI service
const createClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: WORKFLOW_BUILDER_CONFIG.BASE_URL,
    timeout: WORKFLOW_BUILDER_CONFIG.TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  return client;
};

export const useWorkflowBuilder = () => {
  const [session, setSession] = useState<WorkflowBuilderSession>({
    sessionId: null,
    messages: [],
    isLoading: false,
    isConnected: true,
    finalConfig: null,
    isComplete: false,
  });

  const client = createClient();

  const createSession = useCallback(async (projectId: number = 1): Promise<string> => {
    try {
      setSession(prev => ({ ...prev, isLoading: true, isConnected: true }));

      // Use the new two-step session creation:
      // 1. Register with Django (creates WorkflowBuilderSession)
      // 2. Initialize with FastAPI (sets up chat)
      const { default: workflowBuilderApi } = await import('../lib/workflowBuilderApi');
      const response = await workflowBuilderApi.createSession(projectId);
      const sessionId = response.session_id;

      setSession(prev => ({
        ...prev,
        sessionId,
        messages: [],
        finalConfig: null,
        isComplete: false,
        isConnected: true,
      }));

      return sessionId;
    } catch (error) {
      console.error('Failed to create session:', error);
      setSession(prev => ({ ...prev, isConnected: false }));
      throw error;
    } finally {
      setSession(prev => ({ ...prev, isLoading: false }));
    }
  }, []);

  const sendMessage = useCallback(async (message: string): Promise<void> => {
    if (!session.sessionId || session.isLoading) {
      throw new Error('No active session or already loading');
    }

    try {
      setSession(prev => ({ ...prev, isLoading: true }));

      // Add user message immediately
      const userMessage: Message = {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };

      setSession(prev => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // For streaming responses, use fetch
      const response = await fetch(`${WORKFLOW_BUILDER_CONFIG.BASE_URL}${WORKFLOW_BUILDER_CONFIG.GENERATE_ENDPOINT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: message,
          session_id: session.sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      let aiMessage = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = new TextDecoder().decode(value);
        const lines = text.split('\n').filter(line => line.trim());

        for (const line of lines) {
          try {
            const data = JSON.parse(line);

            // Handle structured responses from new multi-agent system
            if (data.role === 'assistant' && data.structured === true) {
              const structuredResponse = data.response;
              let messageContent = '';

              // Extract message based on action type and update workflow config in real-time
              switch (structuredResponse.action_type) {
                case 'conversation':
                  // Show the conversational message
                  messageContent = structuredResponse.data.message;
                  break;

                case 'node_add':
                  messageContent = structuredResponse.message;

                  // Actually add node to workflow config in real-time
                  const nodeData = structuredResponse.data;
                  const newNode = {
                    id: `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                    type: nodeData.node_type,
                    position: nodeData.position || { x: 100, y: 200 },
                    config: nodeData.config || {}
                  };

                  setSession(prev => {
                    const currentNodes = prev.finalConfig?.nodes || [];
                    const currentEdges = prev.finalConfig?.edges || [];
                    const now = new Date().toISOString();

                    return {
                      ...prev,
                      finalConfig: {
                        nodes: [...currentNodes, newNode],
                        edges: currentEdges,
                        metadata: {
                          name: 'Untitled Workflow',
                          description: '',
                          version: '1.0.0',
                          ...(prev.finalConfig?.metadata || {}),
                          created: prev.finalConfig?.metadata?.created || now,
                          updated: now
                        },
                        properties: prev.finalConfig?.properties || {}
                      }
                    };
                  });
                  break;

                case 'edge_add':
                  messageContent = structuredResponse.message;

                  // Add edge connecting nodes
                  const edgeData = structuredResponse.data;
                  const newEdge = {
                    id: `edge-${Date.now()}`,
                    source: edgeData.source,
                    target: edgeData.target,
                    sourceHandle: edgeData.source_handle,
                    targetHandle: edgeData.target_handle
                  };

                  setSession(prev => {
                    const currentEdges = prev.finalConfig?.edges || [];

                    return {
                      ...prev,
                      finalConfig: {
                        ...prev.finalConfig,
                        edges: [...currentEdges, newEdge]
                      }
                    };
                  });
                  break;

                case 'node_edit':
                  messageContent = structuredResponse.message;

                  // Update existing node configuration
                  const editData = structuredResponse.data;
                  setSession(prev => {
                    const updatedNodes = (prev.finalConfig?.nodes || []).map(node =>
                      node.id === editData.node_id
                        ? {
                            ...node,
                            config: { ...node.config, ...editData.config_updates },
                            position: editData.position_update || node.position
                          }
                        : node
                    );

                    return {
                      ...prev,
                      finalConfig: {
                        ...prev.finalConfig,
                        nodes: updatedNodes
                      }
                    };
                  });
                  break;

                case 'node_remove':
                  messageContent = structuredResponse.message;

                  // Remove node and its connected edges
                  const removeData = structuredResponse.data;
                  setSession(prev => {
                    const filteredNodes = (prev.finalConfig?.nodes || []).filter(
                      node => node.id !== removeData.node_id
                    );
                    const filteredEdges = (prev.finalConfig?.edges || []).filter(
                      edge => edge.source !== removeData.node_id && edge.target !== removeData.node_id
                    );

                    return {
                      ...prev,
                      finalConfig: {
                        ...prev.finalConfig,
                        nodes: filteredNodes,
                        edges: filteredEdges
                      }
                    };
                  });
                  break;

                case 'edge_remove':
                  messageContent = structuredResponse.message;

                  // Remove specific edge
                  const edgeRemoveData = structuredResponse.data;
                  setSession(prev => {
                    const filteredEdges = (prev.finalConfig?.edges || []).filter(
                      edge => edge.id !== edgeRemoveData.edge_id
                    );

                    return {
                      ...prev,
                      finalConfig: {
                        ...prev.finalConfig,
                        edges: filteredEdges
                      }
                    };
                  });
                  break;

                case 'workflow_complete':
                  messageContent = structuredResponse.data.summary;

                  // Mark workflow as complete
                  setSession(prev => ({
                    ...prev,
                    isComplete: true
                  }));
                  break;

                default:
                  // Fallback to top-level message
                  messageContent = structuredResponse.message;
              }

              // Update AI message in real-time
              setSession(prev => {
                const newMessages = [...prev.messages];
                const lastMessage = newMessages[newMessages.length - 1];

                if (lastMessage && lastMessage.role === 'model') {
                  // Update existing message
                  lastMessage.content = messageContent;
                  lastMessage.timestamp = data.timestamp || new Date().toISOString();
                } else {
                  // Add new message
                  newMessages.push({
                    role: 'model',
                    content: messageContent,
                    timestamp: data.timestamp || new Date().toISOString(),
                  });
                }

                return { ...prev, messages: newMessages };
              });
            }
            // Handle legacy format (backward compatibility)
            else if (data.role === 'model' && data.content) {
              aiMessage = data.content;

              // Update AI message in real-time
              setSession(prev => {
                const newMessages = [...prev.messages];
                const lastMessage = newMessages[newMessages.length - 1];

                if (lastMessage && lastMessage.role === 'model') {
                  lastMessage.content = aiMessage;
                  lastMessage.timestamp = data.timestamp || new Date().toISOString();
                } else {
                  newMessages.push({
                    role: 'model',
                    content: aiMessage,
                    timestamp: data.timestamp || new Date().toISOString(),
                  });
                }

                return { ...prev, messages: newMessages };
              });
            }
          } catch (e) {
            // Ignore malformed JSON chunks
          }
        }
      }

      // No need to check finalization - workflow updates happen in real-time via structured responses

    } catch (error) {
      console.error('Failed to send message:', error);
      setSession(prev => ({ ...prev, isConnected: false }));
      throw error;
    } finally {
      setSession(prev => ({ ...prev, isLoading: false }));
    }
  }, [session.sessionId, session.isLoading]);

  const checkFinalization = useCallback(async (): Promise<any | null> => {
    if (!session.sessionId) return null;

    try {
      const response = await client.get(
        `${WORKFLOW_BUILDER_CONFIG.GENERATE_FINALIZE_ENDPOINT}?session_id=${session.sessionId}`
      );

      if (response.status === 200) {
        const config = response.data;
        setSession(prev => ({
          ...prev,
          finalConfig: config,
          isComplete: true,
        }));
        return config;
      }

      return null;
    } catch (error: any) {
      // 202 means not finalized yet, not an error
      if (error.response?.status === 202) {
        return null;
      }
      console.error('Failed to check finalization:', error);
      return null;
    }
  }, [session.sessionId]);

  const resetSession = useCallback(async (): Promise<void> => {
    if (!session.sessionId) return;

    try {
      setSession(prev => ({ ...prev, isLoading: true }));

      await client.post(WORKFLOW_BUILDER_CONFIG.RESET_ENDPOINT, {
        session_id: session.sessionId,
      });

      setSession(prev => ({
        ...prev,
        messages: [],
        finalConfig: null,
        isComplete: false,
      }));
    } catch (error) {
      console.error('Failed to reset session:', error);
      setSession(prev => ({ ...prev, isConnected: false }));
      throw error;
    } finally {
      setSession(prev => ({ ...prev, isLoading: false }));
    }
  }, [session.sessionId]);

  const getHistory = useCallback(async (): Promise<Message[]> => {
    if (!session.sessionId) return [];

    try {
      const response = await client.get(
        `/chat/?session_id=${session.sessionId}`
      );

      const text = response.data;
      const lines = text.trim().split('\n');
      const messages: Message[] = [];

      for (const line of lines) {
        if (line.trim()) {
          try {
            const message = JSON.parse(line);
            messages.push(message);
          } catch (e) {
            console.warn('Failed to parse message:', line);
          }
        }
      }

      setSession(prev => ({ ...prev, messages }));
      return messages;
    } catch (error) {
      console.error('Failed to get history:', error);
      setSession(prev => ({ ...prev, isConnected: false }));
      return [];
    }
  }, [session.sessionId]);

  return {
    session,
    createSession,
    sendMessage,
    checkFinalization,
    resetSession,
    getHistory,
  };
};
