import { useState, useCallback } from 'react';
import { AGENT_BUILDER_CONFIG } from '../lib/config';

interface Message {
  role: 'user' | 'model';
  content: string;
  timestamp: string;
}

interface AgentBuilderSession {
  sessionId: string | null;
  messages: Message[];
  isLoading: boolean;
  isConnected: boolean;
  finalConfig: any | null;
  isComplete: boolean;
}

// Helper function for robust API calls
const fetchWithTimeout = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), AGENT_BUILDER_CONFIG.TIMEOUT);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${AGENT_BUILDER_CONFIG.TIMEOUT}ms`);
    }
    throw error;
  }
};

export const useAgentBuilder = () => {
  const [session, setSession] = useState<AgentBuilderSession>({
    sessionId: null,
    messages: [],
    isLoading: false,
    isConnected: true,
    finalConfig: null,
    isComplete: false,
  });

  const createSession = useCallback(async (): Promise<string> => {
    try {
      setSession(prev => ({ ...prev, isLoading: true, isConnected: true }));

      const response = await fetchWithTimeout(`${AGENT_BUILDER_CONFIG.BASE_URL}${AGENT_BUILDER_CONFIG.SESSION_ENDPOINT}`, {
        method: 'POST',
      });

      const data = await response.json();
      const sessionId = data.session_id;

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

      const response = await fetchWithTimeout(`${AGENT_BUILDER_CONFIG.BASE_URL}${AGENT_BUILDER_CONFIG.GENERATE_ENDPOINT}`, {
        method: 'POST',
        body: JSON.stringify({
          prompt: message,
          session_id: session.sessionId,
        }),
      });

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
            if (data.role === 'model') {
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

      // Check if configuration is complete
      await checkFinalization();

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
      const response = await fetchWithTimeout(
        `${AGENT_BUILDER_CONFIG.BASE_URL}${AGENT_BUILDER_CONFIG.GENERATE_FINALIZE_ENDPOINT}?session_id=${session.sessionId}`
      );

      if (response.ok) {
        const config = await response.json();
        setSession(prev => ({
          ...prev,
          finalConfig: config,
          isComplete: true,
        }));
        return config;
      }

      return null;
    } catch (error) {
      console.error('Failed to check finalization:', error);
      return null;
    }
  }, [session.sessionId]);

  const resetSession = useCallback(async (): Promise<void> => {
    if (!session.sessionId) return;

    try {
      setSession(prev => ({ ...prev, isLoading: true }));

      await fetchWithTimeout(`${AGENT_BUILDER_CONFIG.BASE_URL}${AGENT_BUILDER_CONFIG.RESET_ENDPOINT}`, {
        method: 'POST',
        body: JSON.stringify({ session_id: session.sessionId }),
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
      const response = await fetchWithTimeout(
        `${AGENT_BUILDER_CONFIG.BASE_URL}${AGENT_BUILDER_CONFIG.CHAT_ENDPOINT}?session_id=${session.sessionId}`
      );

      const text = await response.text();
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