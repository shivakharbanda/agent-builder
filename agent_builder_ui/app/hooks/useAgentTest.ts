import { useState, useCallback } from 'react';
import { api } from '../lib/api';
import type {
  AgentTestRequest,
  AgentTestResponse,
  ConversationMessage,
  InternalToolAttachment
} from '../lib/types';

interface UseAgentTestResult {
  testing: boolean;
  error: string | null;
  testResult: AgentTestResponse | null;
  conversationHistory: ConversationMessage[];
  sessionId: string;
  runStructuredTest: (inputs: Record<string, any>, credentialId: number, model?: string, mcpServerIds?: number[], internalToolAttachments?: InternalToolAttachment[]) => Promise<void>;
  runUnstructuredTest: (message: string, credentialId: number, model?: string, mcpServerIds?: number[], internalToolAttachments?: InternalToolAttachment[]) => Promise<void>;
  clearConversation: () => void;
  clearResults: () => void;
}

// Generate a unique session ID using modern browser API
function generateSessionId(): string {
  return crypto.randomUUID();
}

export const useAgentTest = (agentId: number): UseAgentTestResult => {
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<AgentTestResponse | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>(() => generateSessionId());

  const runStructuredTest = useCallback(async (
    inputs: Record<string, any>,
    credentialId: number,
    model?: string,
    mcpServerIds?: number[],
    internalToolAttachments?: InternalToolAttachment[]
  ) => {
    try {
      setTesting(true);
      setError(null);
      setTestResult(null);

      const request: AgentTestRequest = {
        test_type: 'structured',
        credential_id: credentialId,
        model,
        inputs,
        mcp_server_ids: mcpServerIds,
        internal_tool_attachments: internalToolAttachments
      };

      const result = await api.testAgent(agentId, request);
      setTestResult(result);

      if (!result.success && result.error) {
        setError(result.error);
      }
    } catch (err: any) {
      setError(err.detail || 'Failed to run test');
      console.error('Failed to run structured test:', err);
    } finally {
      setTesting(false);
    }
  }, [agentId]);

  const runUnstructuredTest = useCallback(async (
    message: string,
    credentialId: number,
    model?: string,
    mcpServerIds?: number[],
    internalToolAttachments?: InternalToolAttachment[]
  ) => {
    try {
      setTesting(true);
      setError(null);

      // Optimistically add user message to conversation history immediately
      // This ensures the user sees their message right away (better UX)
      const userMessage: ConversationMessage = {
        role: 'user',
        content: message
      };
      setConversationHistory(prev => [...prev, userMessage]);

      const request: AgentTestRequest = {
        test_type: 'unstructured',
        credential_id: credentialId,
        model,
        message,
        session_id: sessionId,
        mcp_server_ids: mcpServerIds,
        internal_tool_attachments: internalToolAttachments
      };

      const result = await api.testAgent(agentId, request);
      setTestResult(result);

      if (result.success && result.conversation_history) {
        // Backend returns full conversation history (including user + agent messages)
        setConversationHistory(result.conversation_history);
      } else if (!result.success && result.error) {
        setError(result.error);
        // Remove optimistic message on error
        setConversationHistory(prev => prev.slice(0, -1));
      }
    } catch (err: any) {
      setError(err.detail || 'Failed to run test');
      console.error('Failed to run unstructured test:', err);
      // Remove optimistic message on error
      setConversationHistory(prev => prev.slice(0, -1));
    } finally {
      setTesting(false);
    }
  }, [agentId, sessionId]);

  const clearConversation = useCallback(() => {
    setConversationHistory([]);
    setTestResult(null);
    setError(null);
    setSessionId(generateSessionId()); // Generate new session ID for fresh conversation
  }, []);

  const clearResults = useCallback(() => {
    setTestResult(null);
    setError(null);
  }, []);

  return {
    testing,
    error,
    testResult,
    conversationHistory,
    sessionId,
    runStructuredTest,
    runUnstructuredTest,
    clearConversation,
    clearResults
  };
};
